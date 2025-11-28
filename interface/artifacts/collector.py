"""Main collector class for product artifacts."""

import asyncio
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils import ScenarioPaths, parse_product_identifiers
from scrapers.product_detail_scraper import ProductDetailScraper
from scrapers.html_fetcher import HtmlFetcher
from scrapers.inquiry_scraper import InquiryScraper
from scrapers.quantity_scraper import QuantityScraper
from scrapers.review_scraper import ReviewScraper
from processors.ocr_processor import OCRProcessor

from interface.artifacts.context import ArtifactContext, ArtifactCollectionResult
from interface.artifacts.handlers.btf_handler import BTFHandler
from interface.artifacts.handlers.ocr_handler import OCRHandler
from interface.artifacts.handlers.chunking_handler import ChunkingHandler

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

if load_dotenv:
    load_dotenv()

logger = logging.getLogger(__name__)


class ProductArtifactCollector:
    """Collects product artifacts using the existing crawling utilities."""

    def __init__(
        self,
        *,
        run_dir: Optional[str],
        cookie: Optional[str],
        ocr_delay: float = 0.5,
        ocr_only_btf: bool = True,
        existing_run_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        verbose: bool = True,
        review_pages: int = 1,
        review_page_size: int = 20,
        source: str = "interactive_cli",
        # Dependency Injection
        html_fetcher: Optional[HtmlFetcher] = None,
        review_scraper: Optional[ReviewScraper] = None,
        inquiry_scraper: Optional[InquiryScraper] = None,
        quantity_scraper: Optional[QuantityScraper] = None,
        btf_scraper: Optional[ProductDetailScraper] = None,
    ):
        self.run_dir = run_dir
        self.cookie = cookie
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.ocr_delay = max(ocr_delay, 0.0)
        self.ocr_only_btf = ocr_only_btf
        self._existing_run_dir = Path(existing_run_dir).expanduser() if existing_run_dir else None
        self.verbose = verbose
        self.review_pages = review_pages
        self.review_page_size = review_page_size
        self.source = source

        # Initialize scrapers (use injected or create new)
        self.html_fetcher = html_fetcher or HtmlFetcher(timeout=40, cookie=cookie)
        self.review_scraper = review_scraper or ReviewScraper(cookie=cookie, retries=2)
        self.inquiry_scraper = inquiry_scraper or InquiryScraper(cookie=cookie, retries=2)
        self.quantity_scraper = quantity_scraper or QuantityScraper(cookie=cookie, timeout=60)
        self.btf_scraper = btf_scraper or ProductDetailScraper(cookie=cookie, retries=2)
        
        # Initialize processors
        self.ocr_processor = OCRProcessor(api_key=self.api_key, delay=self.ocr_delay) if self.api_key else None
        
        # Initialize handlers
        self.btf_handler = BTFHandler(self.btf_scraper)
        self.ocr_handler = OCRHandler(self.ocr_processor, delay=self.ocr_delay, only_btf=self.ocr_only_btf)
        self.chunking_handler = ChunkingHandler()

    async def collect(self, product_url: str, preloaded_html: Optional[str] = None) -> ArtifactCollectionResult:
        """Collect artifacts for a product."""
        ctx = self._prepare_context(product_url)
        logger.info("Collecting artifacts for product_id=%s", ctx.product_id)
        
        # Offload the actual synchronous collection to a thread
        summary = await asyncio.to_thread(self._collect_sync, ctx, preloaded_html)
        
        # Start background OCR processing if API key is available
        if self.api_key:
            ocr_thread = threading.Thread(
                target=self._run_background_ocr,
                args=(ctx,),
                daemon=True,
                name=f"OCR-{ctx.product_id}"
            )
            ocr_thread.start()
            logger.info("Started background OCR thread for product_id=%s", ctx.product_id)
        
        logger.info("Collected artifacts for product_id=%s", ctx.product_id)
        chunk_file = summary.get("chunk_dataset_file")
        return ArtifactCollectionResult(
            summary=summary,
            product_id=ctx.product_id,
            item_id=ctx.item_id,
            vendor_item_id=ctx.vendor_item_id,
            paths=ctx.paths,
            chunk_file=chunk_file,
        )

    def _prepare_context(self, product_url: str) -> ArtifactContext:
        product_id, item_id, vendor_item_id = parse_product_identifiers(product_url)

        if self._existing_run_dir:
            run_dir = self._existing_run_dir
            html_dir = run_dir / "html"
            reviews_dir = run_dir / "reviews"
            inquiries_dir = run_dir / "inquiries"
            quantity_dir = run_dir / "quantity"
            for directory in (run_dir, html_dir, reviews_dir, inquiries_dir, quantity_dir):
                directory.mkdir(parents=True, exist_ok=True)
            paths = ScenarioPaths(
                run_dir=run_dir,
                html_dir=html_dir,
                reviews_dir=reviews_dir,
                inquiries_dir=inquiries_dir,
                quantity_dir=quantity_dir,
                summary_file=run_dir / "artifact_summary.json",
            )
        else:
            paths = ScenarioPaths.build(self.run_dir, product_id)

        btf_dir = paths.run_dir / "btf"
        btf_images_dir = btf_dir / "images"
        btf_dir.mkdir(parents=True, exist_ok=True)
        btf_images_dir.mkdir(parents=True, exist_ok=True)
        ocr_results_file = paths.run_dir / f"ocrs_{product_id}.json"
        return ArtifactContext(
            product_url=product_url,
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id,
            paths=paths,
            btf_dir=btf_dir,
            btf_images_dir=btf_images_dir,
            ocr_results_file=ocr_results_file,
        )

    def _collect_sync(self, ctx: ArtifactContext, preloaded_html: Optional[str] = None) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        logger.info("Starting artifact steps for product_id=%s", ctx.product_id)

        def record(name: str, status: str, details: Dict[str, Any]) -> None:
            serialized = {k: (str(v) if isinstance(v, Path) else v) for k, v in details.items()}
            steps.append({"name": name, "status": status, "details": serialized})
            logger.info(
                "[artifact] step=%s status=%s details=%s",
                name,
                status,
                serialized,
            )

            # User-friendly console output
            label_map = {
                "fetch_html": "기본 정보",
                "fetch_reviews": "리뷰",
                "fetch_inquiries": "상품 문의",
                "fetch_quantity": "가격/재고",
                "fetch_btf": "상세 페이지",
                "ocr_processing": "이미지 OCR",
                "build_chunks": "데이터 청킹",
            }
            label = label_map.get(name, name)
            
            if self.verbose:
                if status == "success":
                    print(f"✓ {label} 수집 성공")
                elif status == "skipped":
                    print(f"⚠️  {label} 수집 건너뜀 ({details.get('reason', 'Unknown')})")
                else:
                    print(f"✗ {label} 수집 실패: {details.get('error', 'Unknown')}")

        # HTML
        html_success = False
        try:
            if preloaded_html:
                # Use preloaded HTML from Playwright
                from bs4 import BeautifulSoup
                logger.info("Using preloaded HTML from Playwright (bypassing HTTP clients)")
                
                # Save the HTML
                ctx.paths.html_dir.mkdir(parents=True, exist_ok=True)
                out_path = ctx.paths.html_dir / f"response_{ctx.product_id}.html"
                out_path.write_text(preloaded_html, encoding="utf-8")
                
                # Parse it
                soup = BeautifulSoup(preloaded_html, "html.parser")
                
                # Extract IDs from HTML since we don't have a response URL
                if not ctx.item_id or not ctx.vendor_item_id:
                    # Try JSON-LD SKU first (format: "487322-41045")
                    sku_match = re.search(r'"sku"\s*:\s*"(\d+)-(\d+)"', preloaded_html)
                    if sku_match:
                        if not ctx.item_id:
                            ctx.item_id = sku_match.group(1)  # First part is itemId
                            logger.info(f"SKU에서 추출 성공: itemId={ctx.item_id}")
                        if not ctx.vendor_item_id:
                            ctx.vendor_item_id = sku_match.group(2)  # Second part is vendorItemId
                            logger.info(f"SKU에서 추출 성공: vendorItemId={ctx.vendor_item_id}")
                
                # Fallback: Try more specific regex patterns
                if not ctx.item_id:
                    # Look for itemId in JavaScript object/JSON with number value (not string "1")
                    m_item = re.search(r'["\']itemId["\']\s*:\s*(\d{3,})[,}]', preloaded_html)
                    if m_item:
                        ctx.item_id = m_item.group(1)
                        logger.info(f"HTML Regex 추출 성공: itemId={ctx.item_id}")

                if not ctx.vendor_item_id:
                    m_vendor = re.search(r'["\']vendorItemId["\']\s*:\s*(\d{3,})[,}]', preloaded_html)
                    if m_vendor:
                        ctx.vendor_item_id = m_vendor.group(1)
                        logger.info(f"HTML Regex 추출 성공: vendorItemId={ctx.vendor_item_id}")
                
                html_success = True
                record(
                    "fetch_html",
                    "success",
                    {
                        "status": 200,
                        "url": ctx.product_url,
                        "file": out_path,
                        "title": soup.title.text.strip() if soup.title else "",
                        "resolved_item_id": ctx.item_id,
                        "resolved_vendor_item_id": ctx.vendor_item_id,
                        "source": "playwright_preloaded",
                    },
                )
            else:
                # Use HTTP clients (existing logic)
                resp, soup, out_path = self.html_fetcher.fetch(
                    ctx.product_id,
                    ctx.item_id or "",
                    ctx.vendor_item_id or "",
                    outdir=ctx.paths.html_dir,
                )
                ctx.update_ids_from_url(resp.url)

                # URL에 ID가 없을 경우, HTML 본문에서 직접 추출하는 "구명조끼" 로직 추가
                if not ctx.item_id or not ctx.vendor_item_id:
                    try:
                        page_content = resp.text
                        
                        # 1. Try explicit itemId/vendorItemId regex first (most reliable)
                        if not ctx.item_id:
                            # Match: itemId, originalItemId, "itemId", "originalItemId"
                            item_match = re.search(r'["\']?(?:originalI|i)temId["\']?\s*[:=]\s*["\']?(\d{5,})["\']?', page_content)
                            if item_match:
                                ctx.item_id = item_match.group(1)
                                logger.info(f"HTML Regex 추출 성공: itemId={ctx.item_id}")
                        
                        if not ctx.vendor_item_id:
                            # Match: vendorItemId, originalVendorItemId
                            vendor_match = re.search(r'["\']?(?:originalV|v)endorItemId["\']?\s*[:=]\s*["\']?(\d{5,})["\']?', page_content)
                            if vendor_match:
                                ctx.vendor_item_id = vendor_match.group(1)
                                logger.info(f"HTML Regex 추출 성공: vendorItemId={ctx.vendor_item_id}")

                        # 2. Fallback to SKU if still missing
                        if not ctx.item_id or not ctx.vendor_item_id:
                            sku_match = re.search(r'"sku"\s*:\s*"(\d+)-(\d+)"', page_content)
                            if sku_match:
                                if not ctx.item_id:
                                    ctx.item_id = sku_match.group(2)
                                    logger.info(f"SKU에서 추출 성공: itemId={ctx.item_id}")
                                if not ctx.vendor_item_id:
                                    ctx.vendor_item_id = sku_match.group(2)
                                    logger.info(f"SKU에서 추출 성공: vendorItemId={ctx.vendor_item_id}")
                    except Exception as e:
                        logger.warning(f"ID 추출 중 오류 발생: {e}")

                html_success = True
                record(
                    "fetch_html",
                    "success",
                    {
                        "status": resp.status_code,
                        "url": resp.url,
                        "file": out_path,
                        "title": soup.title.text.strip() if soup.title else "",
                        "resolved_item_id": ctx.item_id,
                        "resolved_vendor_item_id": ctx.vendor_item_id,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            record("fetch_html", "error", {"error": str(exc)})

        # If HTML failed, skip everything else
        if not html_success:
            record("fetch_reviews", "skipped", {"reason": "HTML 수집 실패"})
            record("fetch_inquiries", "skipped", {"reason": "HTML 수집 실패"})
            record("fetch_quantity", "skipped", {"reason": "HTML 수집 실패"})
            record("fetch_btf", "skipped", {"reason": "HTML 수집 실패"})
            record("ocr_processing", "skipped", {"reason": "HTML 수집 실패"})
            record("build_chunks", "skipped", {"reason": "HTML 수집 실패"})
            
            summary = {
                "product_url": ctx.product_url,
                "product_id": ctx.product_id,
                "steps": steps,
                "source": self.source,
                "collected_at": int(time.time()),
            }
            self._persist_summary(ctx, summary)
            return summary

        # Reviews
        try:
            page_records: List[Dict[str, Any]] = []
            for page_no in range(1, self.review_pages + 1):
                resp, data = self.review_scraper.fetch(
                    product_id=ctx.product_id,
                    vendor_item_id=ctx.vendor_item_id,
                    item_id=ctx.item_id,
                    page=page_no,
                    size=self.review_page_size,
                    outdir=ctx.paths.reviews_dir,
                )
                page_records.append(
                    {
                        "page": page_no,
                        "status": resp.status_code,
                        "response_keys": list(data.keys()),
                    }
                )
            record(
                "fetch_reviews",
                "success",
                {"output_dir": ctx.paths.reviews_dir, "pages": page_records},
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_reviews", "error", {"error": str(exc)})

        # Inquiries
        try:
            resp, data = self.inquiry_scraper.fetch(
                product_id=ctx.product_id,
                page_no=1,
                item_id=ctx.item_id,
                vendor_item_id=ctx.vendor_item_id,
                outdir=ctx.paths.inquiries_dir,
                is_preview=True,
            )
            record(
                "fetch_inquiries",
                "success",
                {
                    "output_dir": ctx.paths.inquiries_dir,
                    "status": resp.status_code,
                    "response_keys": list(data.keys()),
                    "page_no": 1,
                },
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_inquiries", "error", {"error": str(exc)})

        # Quantity
        # ------------------------------------------------------------------
        # [DEBUG LOG] ID 수집 상태 확인용 로그 추가
        # ------------------------------------------------------------------
        print(f"\n[DEBUG] Quantity 수집 시작 전 ID 확인:")
        print(f"  - productId: {ctx.product_id}")
        print(f"  - itemId: {ctx.item_id}")
        print(f"  - vendorItemId: {ctx.vendor_item_id}")
        # ------------------------------------------------------------------

        if ctx.item_id and ctx.vendor_item_id:
            try:
                resp, data = self.quantity_scraper.fetch(
                    ctx.product_id,
                    ctx.item_id,
                    ctx.vendor_item_id,
                    outdir=ctx.paths.quantity_dir,
                )
                record(
                    "fetch_quantity",
                    "success",
                    {
                        "status": resp.status_code,
                        "output_dir": ctx.paths.quantity_dir,
                        "keys": list(data.keys()) if isinstance(data, dict) else f"List[{len(data)}]",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                record("fetch_quantity", "error", {"error": str(exc)})
        else:
            record(
                "fetch_quantity",
                "skipped",
                {"reason": "itemId 또는 vendorItemId가 없어 quantity 수집을 건너뜁니다."},
            )

        # BTF payload + images (Delegated to BTFHandler)
        try:
            btf_details = self.btf_handler.fetch_and_process(ctx)
            ctx.btf_image_mapping = btf_details.get("image_url_to_path", {})  # Store for chunker
            record("fetch_btf", "success", btf_details)
        except Exception as exc:  # noqa: BLE001
            record("fetch_btf", "error", {"error": str(exc)})


        # OCR - Skip in sync collection, will run in background
        # This allows summary generation to proceed immediately
        if self.api_key:
            record("ocr_processing", "pending", {"reason": "OCR processing in background"})
        else:
            record(
                "ocr_processing",
                "skipped",
                {
                    "reason": "OPENAI_API_KEY 미설정",
                    "hint": "환경 변수 또는 CLI 옵션으로 설정하면 이미지 OCR을 활성화할 수 있습니다.",
                },
            )


        # Chunking (Delegated to ChunkingHandler)
        chunk_file: Optional[str] = None
        try:
            chunk_details = self.chunking_handler.build_dataset(ctx)
            if chunk_details:
                chunk_file = chunk_details.get("file")
                record("build_chunks", "success", chunk_details)
            else:
                record(
                    "build_chunks",
                    "skipped",
                    {"reason": "수집된 데이터를 기반으로 청크를 생성할 수 없습니다."},
                )
        except Exception as exc:  # noqa: BLE001
            record("build_chunks", "error", {"error": str(exc)})

        summary = {
            "product_url": ctx.product_url,
            "product_id": ctx.product_id,
            "item_id": ctx.item_id,
            "vendor_item_id": ctx.vendor_item_id,
            "paths": {
                "run_dir": str(ctx.paths.run_dir),
                "html_dir": str(ctx.paths.html_dir),
                "reviews_dir": str(ctx.paths.reviews_dir),
                "inquiries_dir": str(ctx.paths.inquiries_dir),
                "quantity_dir": str(ctx.paths.quantity_dir),
                "btf_dir": str(ctx.btf_dir),
                "btf_images_dir": str(ctx.btf_images_dir),
                "ocr_file": str(ctx.ocr_results_file) if ctx.ocr_results_file.exists() else None,
            },
            "steps": steps,
            "source": self.source,
            "collected_at": int(time.time()),
            "chunk_dataset_file": chunk_file,
        }
        self._persist_summary(ctx, summary)
        logger.info(
            "Artifact summary finalized for product_id=%s (run_dir=%s)",
            ctx.product_id,
            ctx.paths.run_dir,
        )
        return summary

    def _persist_summary(self, ctx: ArtifactContext, summary: Dict[str, Any]) -> None:
        try:
            ctx.paths.summary_file.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Persisted artifact summary to %s", ctx.paths.summary_file)
        except Exception:
            logger.exception("Failed to persist artifact summary for product_id=%s", ctx.product_id)
            pass

    def _run_background_ocr(self, ctx: ArtifactContext) -> None:
        """
        Run OCR processing in background thread and update dataset.
        
        This method:
        1. Runs OCR on product images
        2. Re-generates chunks including OCR data
        3. Updates summary file with OCR completion status
        """
        try:
            logger.info("[Background OCR] Starting for product_id=%s", ctx.product_id)
            
            # Run OCR
            status, details = self.ocr_handler.process(ctx)
            logger.info("[Background OCR] OCR completed with status=%s", status)
            
            # Re-run chunking to include OCR data
            chunk_details = self.chunking_handler.build_dataset(ctx)
            if chunk_details:
                logger.info("[Background OCR] Updated chunks with OCR data: %s", chunk_details.get("file"))
            
            # Update summary file with OCR completion status
            try:
                summary_path = ctx.paths.summary_file
                if summary_path.exists():
                    with summary_path.open("r", encoding="utf-8") as f:
                        summary = json.load(f)
                    
                    # Update OCR step status
                    for step in summary.get("steps", []):
                        if step.get("name") == "ocr_processing":
                            step["status"] = status
                            step["details"] = details
                            break
                    
                    # Add OCR completion timestamp
                    summary["ocr_completed_at"] = int(time.time())
                    
                    # Update chunk file path if re-chunking succeeded
                    if chunk_details:
                        summary["chunk_dataset_file"] = chunk_details.get("file")
                    
                    with summary_path.open("w", encoding="utf-8") as f:
                        json.dump(summary, f, ensure_ascii=False, indent=2)
                    
                    logger.info("[Background OCR] Updated summary file with OCR results")
            except Exception as e:
                logger.exception("[Background OCR] Failed to update summary file: %s", e)
            
            logger.info("[Background OCR] Completed for product_id=%s", ctx.product_id)
            
        except Exception as e:
            logger.exception("[Background OCR] Failed for product_id=%s: %s", ctx.product_id, e)