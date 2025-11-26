"""Scenario-aware pipeline that couples the crawling stack with the Playwright agent.

This module reuses the crawling utilities from ``DS_project/crawling`` (see
``fetch_html.py``, ``review.py``, ``inquiries.py``, ``quantity.py``, and the
``CoupangCrawlingPipeline`` conventions in ``main.py``/``test_pipeline.py``) to
prepare structured data before exercising the interactive dialog implemented in
``coupang_playwright_agent.py``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright

from .coupang_playwright_agent import CoupangProductAgent
from crawling.fetch_html import fetch_html as fetch_product_html
from crawling.review import fetch_reviews
from crawling.inquiries import fetch_inquiries
from crawling.quantity import fetch_quantity_info


PRODUCT_ID_PATTERN = re.compile(r"/products/(?P<pid>\d+)")


@dataclass
class ScenarioConfig:
    url: str
    question: str
    follow_up: str
    cookie_file: Optional[str]
    run_dir: Optional[str]
    headless: bool
    review_pages: int
    review_page_size: int
    inquiry_page: int
    inquiry_preview: bool
    collect_quantity: bool
    retries: int
    search_timeout: float


@dataclass
class ScenarioPaths:
    run_dir: Path
    html_dir: Path
    reviews_dir: Path
    inquiries_dir: Path
    quantity_dir: Path
    summary_file: Path

    @classmethod
    def build(cls, base_dir: Optional[str], product_id: str) -> "ScenarioPaths":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(base_dir or "outputs/scenario_runs").expanduser()
        run_dir = base / f"{product_id}_{timestamp}"
        html_dir = run_dir / "html"
        reviews_dir = run_dir / "reviews"
        inquiries_dir = run_dir / "inquiries"
        quantity_dir = run_dir / "quantity"
        for directory in (run_dir, html_dir, reviews_dir, inquiries_dir, quantity_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return cls(
            run_dir=run_dir,
            html_dir=html_dir,
            reviews_dir=reviews_dir,
            inquiries_dir=inquiries_dir,
            quantity_dir=quantity_dir,
            summary_file=run_dir / "scenario_summary.json",
        )


@dataclass
class StepResult:
    name: str
    status: str
    details: Dict[str, Any] = field(default_factory=dict)


def parse_product_identifiers(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    match = PRODUCT_ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"URL에서 productId를 찾지 못했습니다: {url}")
    product_id = match.group("pid")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    item_id = (query.get("itemId") or [None])[0]
    vendor_item_id = (query.get("vendorItemId") or [None])[0]
    return product_id, item_id, vendor_item_id


class CoupangScenarioPipeline:
    """High-level orchestrator for the product-page dialog scenario."""

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.product_id, self.item_id, self.vendor_item_id = parse_product_identifiers(config.url)
        self.paths = ScenarioPaths.build(config.run_dir, self.product_id)
        self.cookie_text = self._load_cookie_text(config.cookie_file)
        self.results: List[StepResult] = []
        self.dialog_result: Optional[Dict[str, Any]] = None
        self.artifact_summary: Optional[Dict[str, Any]] = None
        self.chunk_data_path: Optional[str] = None

    def _load_cookie_text(self, cookie_file: Optional[str]) -> Optional[str]:
        if not cookie_file:
            return None
        path = Path(cookie_file).expanduser()
        if not path.is_file():
            print(f"⚠️  Cookie file not found: {cookie_file}")
            return None
        return path.read_text(encoding="utf-8").strip()

    def collect_data(self) -> None:
        self._run_step("fetch_html", self._step_fetch_html)
        self._run_step("fetch_reviews", self._step_fetch_reviews)
        self._run_step("fetch_inquiries", self._step_fetch_inquiries)
        if self.config.collect_quantity:
            if self.item_id and self.vendor_item_id:
                self._run_step("fetch_quantity", self._step_fetch_quantity)
            else:
                self._record_step(
                    "fetch_quantity",
                    "skipped",
                    {
                        "reason": "itemId 또는 vendorItemId가 없어 quantity 수집을 건너뜁니다.",
                        "hint": "URL에 itemId/vendorItemId 쿼리 파라미터를 포함하거나 fetch_html 단계에서 확인한 최종 URL을 사용하세요.",
                    },
                )

    async def run(self) -> Dict[str, Any]:
        self.collect_data()
        await self._collect_additional_artifacts()
        self.dialog_result = await self._run_agent_dialog()
        summary = self._write_summary()
        print(f"\n✓ Scenario artifacts saved under: {self.paths.run_dir}")
        return summary

    def _run_step(self, name: str, func: Callable[[], Dict[str, Any]]) -> None:
        try:
            details = func()
            self._record_step(name, "success", details)
        except Exception as exc:  # noqa: BLE001
            self._record_step(name, "error", {"error": str(exc)})

    def _record_step(self, name: str, status: str, details: Dict[str, Any]) -> None:
        serializable_details = {
            k: (str(v) if isinstance(v, Path) else v) for k, v in details.items()
        }
        self.results.append(StepResult(name=name, status=status, details=serializable_details))

    def _step_fetch_html(self) -> Dict[str, Any]:
        resp, soup, out_path = fetch_product_html(
            self.product_id,
            self.item_id or "",
            self.vendor_item_id or "",
            cookie=self.cookie_text,
            timeout=40,
            outdir=self.paths.html_dir,
        )
        self._update_ids_from_url(resp.url)
        title = soup.title.text.strip() if soup.title else ""
        return {
            "status": resp.status_code,
            "url": resp.url,
            "file": str(out_path),
            "title": title,
            "resolved_item_id": self.item_id,
            "resolved_vendor_item_id": self.vendor_item_id,
        }

    def _step_fetch_reviews(self) -> Dict[str, Any]:
        page_records: List[Dict[str, Any]] = []
        for page_no in range(1, self.config.review_pages + 1):
            resp, data = fetch_reviews(
                product_id=self.product_id,
                vendor_item_id=self.vendor_item_id,
                item_id=self.item_id,
                cookie=self.cookie_text,
                page=page_no,
                size=self.config.review_page_size,
                outdir=str(self.paths.reviews_dir),
                retries=self.config.retries,
            )
            page_records.append(
                {
                    "page": page_no,
                    "status": resp.status_code,
                    "response_keys": list(data.keys()),
                }
            )
        return {"output_dir": str(self.paths.reviews_dir), "pages": page_records}

    def _step_fetch_inquiries(self) -> Dict[str, Any]:
        resp, data = fetch_inquiries(
            product_id=self.product_id,
            page_no=self.config.inquiry_page,
            cookie=self.cookie_text,
            item_id=self.item_id,
            vendor_item_id=self.vendor_item_id,
            outdir=str(self.paths.inquiries_dir),
            retries=self.config.retries,
            is_preview=self.config.inquiry_preview,
        )
        return {
            "output_dir": str(self.paths.inquiries_dir),
            "status": resp.status_code,
            "response_keys": list(data.keys()),
            "page_no": self.config.inquiry_page,
        }

    def _step_fetch_quantity(self) -> Dict[str, Any]:
        resp, data = fetch_quantity_info(
            self.product_id,
            self.item_id,
            self.vendor_item_id,
            cookie=self.cookie_text,
            outdir=str(self.paths.quantity_dir),
        )
        return {
            "status": resp.status_code,
            "output_dir": str(self.paths.quantity_dir),
            "keys": list(data.keys()),
        }

    async def _run_agent_dialog(self) -> Dict[str, Any]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.config.headless)
            page = await browser.new_page()
            await page.goto(self.config.url)

            agent = CoupangProductAgent(
                page,
                search_timeout=self.config.search_timeout,
                chunk_data_path=self.chunk_data_path,
            )
            answer = await agent.answer_user_question(self.config.question)
            if "장바구니" in self.config.follow_up:
                follow_up = await agent.add_product_to_cart()
                branch = "add_to_cart"
            elif "맘에 안" in self.config.follow_up:
                follow_up = await agent.ask_for_preference_feedback()
                branch = "preference_feedback"
            else:
                follow_up = "후속 요청을 인식하지 못했습니다. 다른 문장을 시도해 주세요."
                branch = "fallback"

            await browser.close()

        transcript = {
            "initial_question": self.config.question,
            "initial_answer": answer,
            "follow_up": self.config.follow_up,
            "follow_up_answer": follow_up,
            "branch": branch,
        }
        print("\n[Scenario Transcript]")
        print(f"USER : {self.config.question}")
        print(f"SYSTEM: {answer}")
        print(f"USER : {self.config.follow_up}")
        print(f"SYSTEM: {follow_up}")
        return transcript

    def _update_ids_from_url(self, url: Optional[str]) -> None:
        if not url:
            return
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.item_id = self.item_id or (query.get("itemId") or [None])[0]
        self.vendor_item_id = self.vendor_item_id or (query.get("vendorItemId") or [None])[0]

    def _write_summary(self) -> Dict[str, Any]:
        summary = {
            "product_url": self.config.url,
            "product_id": self.product_id,
            "item_id": self.item_id,
            "vendor_item_id": self.vendor_item_id,
            "paths": {
                "run_dir": str(self.paths.run_dir),
                "html_dir": str(self.paths.html_dir),
                "reviews_dir": str(self.paths.reviews_dir),
                "inquiries_dir": str(self.paths.inquiries_dir),
                "quantity_dir": str(self.paths.quantity_dir),
                "summary_file": str(self.paths.summary_file),
            },
            "steps": [asdict(result) for result in self.results],
            "dialog": self.dialog_result,
            "artifact_summary": self.artifact_summary,
            "chunk_data_path": self.chunk_data_path,
        }
        self.paths.summary_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    async def _collect_additional_artifacts(self) -> None:
        from agent.interactive_cli.artifacts import ProductArtifactCollector

        collector = ProductArtifactCollector(
            run_dir=self.config.run_dir,
            cookie=self.cookie_text,
            existing_run_dir=str(self.paths.run_dir),
        )
        try:
            result = await collector.collect(self.config.url)
        except Exception as exc:  # noqa: BLE001
            self._record_step("collect_artifacts", "error", {"error": str(exc)})
            return

        self.artifact_summary = result.summary
        self.chunk_data_path = result.chunk_file
        details = {
            "chunk_file": result.chunk_file,
            "ocr_file": result.summary.get("paths", {}).get("ocr_file"),
            "btf_dir": result.summary.get("paths", {}).get("btf_dir"),
        }
        self._record_step("collect_artifacts", "success", details)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Coupang product artifacts and execute the Playwright dialog scenario.",
    )
    parser.add_argument("--url", required=True, help="상품 상세 URL (https://www.coupang.com/vp/products/...)")
    parser.add_argument(
        "--question",
        default="발볼 넓은 사람도 신을 수 있대?",
        help="리뷰/문의에서 답변할 초기 질문",
    )
    parser.add_argument(
        "--follow-up",
        dest="follow_up",
        default="좋아, 장바구니 넣어줘",
        help="후속 사용자 발화",
    )
    parser.add_argument("--cookie-file", help="인증이 필요한 단계(리뷰/문의/수량)용 쿠키 파일 경로")
    parser.add_argument(
        "--run-dir",
        help="출력 루트 디렉터리 (기본: outputs/scenario_runs 하위 timestamp 디렉터리)",
    )
    parser.add_argument("--headless", action="store_true", help="Playwright를 headless 모드로 실행")
    parser.add_argument("--review-pages", type=int, default=1, help="리뷰를 요청할 페이지 수")
    parser.add_argument("--review-page-size", type=int, default=20, help="리뷰 API page size")
    parser.add_argument("--inquiry-page", type=int, default=1, help="문의 API page 번호")
    parser.add_argument(
        "--no-inquiry-preview",
        dest="inquiry_preview",
        action="store_false",
        help="문의 API 호출 시 isPreview=false 로 설정",
    )
    parser.set_defaults(inquiry_preview=True)
    parser.add_argument(
        "--collect-quantity",
        action="store_true",
        help="수량/재고 API까지 호출 (itemId & vendorItemId 필요)",
    )
    parser.add_argument("--retries", type=int, default=2, help="리뷰/문의 요청 재시도 횟수")
    parser.add_argument(
        "--search-timeout",
        type=float,
        default=1.5,
        help="Playwright agent가 DOM 요소를 찾을 때 사용하는 기본 타임아웃(초)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = ScenarioConfig(
        url=args.url,
        question=args.question,
        follow_up=args.follow_up,
        cookie_file=args.cookie_file,
        run_dir=args.run_dir,
        headless=args.headless,
        review_pages=args.review_pages,
        review_page_size=args.review_page_size,
        inquiry_page=args.inquiry_page,
        inquiry_preview=args.inquiry_preview,
        collect_quantity=args.collect_quantity,
        retries=args.retries,
        search_timeout=args.search_timeout,
    )
    pipeline = CoupangScenarioPipeline(config)
    asyncio.run(pipeline.run())


if __name__ == "__main__":
    main()
