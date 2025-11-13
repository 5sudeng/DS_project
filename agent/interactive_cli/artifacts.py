"""Artifact collection helpers for the interactive shopping CLI."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

from agent.coupang_scenario_pipeline import ScenarioPaths, parse_product_identifiers
from crawling.btf import fetch_btf
from crawling.fetch_html import fetch_html as fetch_product_html
from crawling.inquiries import fetch_inquiries
from crawling.quantity import fetch_quantity_info
from crawling.review import fetch_reviews
from preprocessing.data_chunking_processor import DataChunker

logger = logging.getLogger(__name__)


@dataclass
class ArtifactCollectionResult:
    summary: Dict[str, Any]
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths
    chunk_file: Optional[str]


@dataclass
class _ArtifactContext:
    product_url: str
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths
    btf_dir: Path
    btf_images_dir: Path

    def update_ids_from_url(self, url: Optional[str]) -> None:
        if not url:
            return
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.item_id = self.item_id or (query.get("itemId") or [None])[0]
        self.vendor_item_id = self.vendor_item_id or (query.get("vendorItemId") or [None])[0]


class ProductArtifactCollector:
    """Collects product artifacts using the existing crawling utilities."""

    def __init__(self, *, run_dir: Optional[str], cookie: Optional[str]):
        self.run_dir = run_dir
        self.cookie = cookie

    async def collect(self, product_url: str) -> ArtifactCollectionResult:
        ctx = self._prepare_context(product_url)
        logger.info("Collecting artifacts for product_id=%s", ctx.product_id)
        summary = await asyncio.to_thread(self._collect_sync, ctx)
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

    def _prepare_context(self, product_url: str) -> _ArtifactContext:
        product_id, item_id, vendor_item_id = parse_product_identifiers(product_url)
        paths = ScenarioPaths.build(self.run_dir, product_id)
        btf_dir = paths.run_dir / "btf"
        btf_images_dir = btf_dir / "images"
        btf_dir.mkdir(parents=True, exist_ok=True)
        btf_images_dir.mkdir(parents=True, exist_ok=True)
        return _ArtifactContext(
            product_url=product_url,
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id,
            paths=paths,
            btf_dir=btf_dir,
            btf_images_dir=btf_images_dir,
        )

    def _collect_sync(self, ctx: _ArtifactContext) -> Dict[str, Any]:
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

        # HTML
        try:
            resp, soup, out_path = fetch_product_html(
                ctx.product_id,
                ctx.item_id or "",
                ctx.vendor_item_id or "",
                cookie=self.cookie,
                timeout=40,
                outdir=ctx.paths.html_dir,
            )
            ctx.update_ids_from_url(resp.url)
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

        # Reviews
        try:
            review_pages = 1
            review_page_size = 20
            page_records: List[Dict[str, Any]] = []
            for page_no in range(1, review_pages + 1):
                resp, data = fetch_reviews(
                    product_id=ctx.product_id,
                    vendor_item_id=ctx.vendor_item_id,
                    item_id=ctx.item_id,
                    cookie=self.cookie,
                    page=page_no,
                    size=review_page_size,
                    outdir=str(ctx.paths.reviews_dir),
                    retries=2,
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
            resp, data = fetch_inquiries(
                product_id=ctx.product_id,
                page_no=1,
                cookie=self.cookie,
                item_id=ctx.item_id,
                vendor_item_id=ctx.vendor_item_id,
                outdir=str(ctx.paths.inquiries_dir),
                retries=2,
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
        if ctx.item_id and ctx.vendor_item_id:
            try:
                resp, data = fetch_quantity_info(
                    ctx.product_id,
                    ctx.item_id,
                    ctx.vendor_item_id,
                    cookie=self.cookie,
                    outdir=str(ctx.paths.quantity_dir),
                )
                record(
                    "fetch_quantity",
                    "success",
                    {
                        "status": resp.status_code,
                        "output_dir": ctx.paths.quantity_dir,
                        "keys": list(data.keys()),
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

        # BTF payload + images
        try:
            btf_details = self._fetch_btf_assets(ctx)
            record("fetch_btf", "success", btf_details)
        except Exception as exc:  # noqa: BLE001
            record("fetch_btf", "error", {"error": str(exc)})

        chunk_file: Optional[str] = None
        try:
            chunk_details = self._build_chunk_dataset(ctx)
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
            },
            "steps": steps,
            "source": "interactive_cli",
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

    def _build_chunk_dataset(self, ctx: _ArtifactContext) -> Optional[Dict[str, Any]]:
        chunker = DataChunker()
        processed_sources: Set[str] = set()

        def _read_text(path: Path) -> Optional[str]:
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    return handle.read()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to read text file %s", path)
                return None

        def _read_json(path: Path) -> Optional[Any]:
            text = _read_text(path)
            if text is None:
                return None
            try:
                return json.loads(text)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to parse JSON file %s", path)
                return None

        html_dir = ctx.paths.html_dir
        if html_dir.exists():
            for html_file in html_dir.glob("*.html"):
                html_text = _read_text(html_file)
                if not html_text:
                    continue
                try:
                    chunker.process_html(html_file.name, html_text)
                    processed_sources.add("html")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking HTML failed for %s", html_file)

        reviews_dir = ctx.paths.reviews_dir
        if reviews_dir.exists():
            for review_file in reviews_dir.glob("*.json"):
                data = _read_json(review_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_reviews(review_file.name, data)
                    processed_sources.add("reviews")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking review file failed for %s", review_file)

        inquiries_dir = ctx.paths.inquiries_dir
        if inquiries_dir.exists():
            for inquiry_file in inquiries_dir.glob("*.json"):
                data = _read_json(inquiry_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_inquiries(inquiry_file.name, data)
                    processed_sources.add("inquiries")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking inquiry file failed for %s", inquiry_file)

        quantity_dir = ctx.paths.quantity_dir
        if quantity_dir.exists():
            for quantity_file in quantity_dir.glob("*.json"):
                data = _read_json(quantity_file)
                if not isinstance(data, list):
                    continue
                try:
                    chunker.process_quantity_json(quantity_file.name, data)
                    processed_sources.add("quantity")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking quantity file failed for %s", quantity_file)

        btf_dir = ctx.btf_dir
        if btf_dir.exists():
            for btf_file in btf_dir.glob("*.json"):
                data = _read_json(btf_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_btf_json(btf_file.name, data)
                    processed_sources.add("btf")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking BTF file failed for %s", btf_file)

        if not chunker.all_chunks:
            return None

        output_path = ctx.paths.run_dir / "chunked_data_output.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(chunker.all_chunks, handle, ensure_ascii=False, indent=2)

        return {
            "file": str(output_path),
            "chunk_count": len(chunker.all_chunks),
            "sources": sorted(processed_sources),
        }

    def _fetch_btf_assets(self, ctx: _ArtifactContext) -> Dict[str, Any]:
        resp, payload = fetch_btf(
            ctx.product_id,
            ctx.item_id,
            ctx.vendor_item_id,
            cookie=self.cookie,
            outdir=None,
            retries=2,
        )

        json_path: Optional[Path] = None
        if ctx.btf_dir:
            json_path = ctx.btf_dir / f"btf_{ctx.product_id}_{int(time.time() * 1000)}.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        normalized_payload = payload.get("response", payload) if isinstance(payload, dict) else payload
        image_urls = self._extract_btf_image_urls(ctx, normalized_payload)
        downloaded = self._download_btf_images(ctx, image_urls)

        return {
            "status": resp.status_code,
            "api_url": resp.url,
            "json_file": str(json_path) if json_path else None,
            "raw_image_urls": image_urls,
            "downloaded_images": downloaded,
            "image_count": len(downloaded),
        }

    def _extract_btf_image_urls(self, ctx: _ArtifactContext, payload: Any) -> List[str]:
        urls: Set[str] = set()
        if isinstance(payload, dict):
            details = payload.get("details") or []
            for detail_block in details:
                if not isinstance(detail_block, dict):
                    continue
                descriptions = detail_block.get("vendorItemContentDescriptions") or []
                for desc in descriptions:
                    if (
                        isinstance(desc, dict)
                        and desc.get("detailType") == "IMAGE"
                        and desc.get("content")
                    ):
                        urls.add(self._normalize_image_url(desc["content"]))

        try:
            serialized = json.dumps(payload, ensure_ascii=False)
            for match in re.findall(r'(//[^"\\s]+image/(?:retail|vendor|product)/[^"\\s]+)', serialized):
                urls.add(self._normalize_image_url(match))
        except TypeError:
            pass

        return [u for u in urls if u]

    def _download_btf_images(self, ctx: _ArtifactContext, urls: List[str]) -> List[str]:
        if not urls:
            return []

        saved: List[str] = []
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        for url in urls:
            normalized = self._normalize_image_url(url)
            if not normalized:
                continue
            filename = self._btf_image_filename(ctx, normalized)
            path = ctx.btf_images_dir / filename
            if path.exists():
                saved.append(str(path))
                continue
            try:
                urllib.request.urlretrieve(normalized, path)
                saved.append(str(path))
            except Exception:
                continue
        return saved

    def _btf_image_filename(self, ctx: _ArtifactContext, url: str) -> str:
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        return f"btf_{ctx.product_id}_{digest}{ext}"

    def _normalize_image_url(self, url: str) -> str:
        if not url:
            return ""
        cleaned = url.strip().rstrip("\\")
        if cleaned.startswith("//"):
            return "https:" + cleaned
        return cleaned

    def _persist_summary(self, ctx: _ArtifactContext, summary: Dict[str, Any]) -> None:
        try:
            ctx.paths.summary_file.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Persisted artifact summary to %s", ctx.paths.summary_file)
        except Exception:
            logger.exception("Failed to persist artifact summary for product_id=%s", ctx.product_id)
            pass
