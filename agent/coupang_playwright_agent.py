"""Playwright-based Coupang shopping assistant agent.

This module implements scenario logic for interacting with a Coupang product
page after navigation has already happened.  The agent supports the following
capabilities:

2. Add the product to the shopping cart when the user confirms interest.
3. Ask the user for feedback and trigger a refreshed search flow if the user is
   not satisfied.

The implementation focuses on the conversation fragment described in the
product detail page scenario:

User:  "발볼 넓은 사람도 신을 수 있대?"
System: "구매 후기에서 ‘발볼이 넓어도 편하게 맞는다’는 평가가 있었습니다. 대부분
         정사이즈를 추천하고 있습니다."
User A: "좋아, 장바구니 넣어줘"  -> add to cart.
User B: "맘에 안들어" -> ask for more details and refresh search terms.

The module exposes a ``CoupangProductAgent`` class which operates on a
``playwright.async_api.Page`` instance.  The class only assumes that the page is
already on a valid product detail view and encapsulates all DOM interaction,
including multiple fallbacks to support layout variations on Coupang.

Example usage (interactive demo):

.. code-block:: python

    import asyncio
    from agent.coupang_playwright_agent import run_demo

    asyncio.run(run_demo(
        url="https://www.coupang.com/vp/products/XXXXX",
        user_follow_up="좋아, 장바구니 넣어줘"
    ))

The demo function can be executed with scenario A or B by toggling the
``user_follow_up`` argument.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
import os

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from agent.llm_utils import ShoppingAssistantLLM


@dataclass

class CoupangProductAgent:
    """Playwright-driven helper that supports the product-page dialog."""

    DEFAULT_CHUNK_DATA_PATH = Path("data/exports_normalized/chunked_data_output.json")

    REVIEW_SECTION_SELECTORS: Sequence[str] = (
        "section[data-coupang='product-review']",
        "div.sdp-review__article__list",
        "div.js_reviewArticleList",
        "section:has-text('상품평')",
    )

    INQUIRY_SECTION_SELECTORS: Sequence[str] = (
        "section[data-coupang='product-qna']",
        "div.sdp-review__article__list__QnA",
        "section:has-text('상품 Q&A')",
        "section:has-text('상품문의')",
    )
    DETAIL_SECTION_SELECTORS: Sequence[str] = (
        "section[data-coupang='product-detail']",
        "div#prodDetail",
        "div.product-detail",
        "div.prod-description",
        "div.sdp-description",
    )
    SPEC_SECTION_SELECTORS: Sequence[str] = (
        "section:has-text('상품정보 제공고시')",
        "section:has-text('상품 정보')",
        "table.prod-delivery-policy",
        "table.prod-delivery-return-policy",
    )

    ADD_TO_CART_SELECTORS: Sequence[str] = (
        "button[data-coupang='add-to-cart']",
        "button[data-trigger='add-to-cart']",
        "button:has-text('장바구니')",
        "button:has-text('장바구니 담기')",
        "button:has-text('장바구니에 담기')",
    )

    CART_CONFIRMATION_SELECTORS: Sequence[str] = (
        "div.cart-confirm",
        "div.layer-popup",
        "div.modal:has-text('장바구니')",
    )

    def __init__(
        self,
        page: Page,
        *,
        search_timeout: float = 1.5,
        chunk_data_path: Optional[str] = None,
        test_mode: Optional[bool] = None,
    ) -> None:
        self.page = page
        self.search_timeout = search_timeout
        self._llm: Optional[ShoppingAssistantLLM] = None
        self._llm_initialized = False
        self.chunk_data_path = (
            Path(chunk_data_path).expanduser() if chunk_data_path else self.DEFAULT_CHUNK_DATA_PATH
        )
        self._chunk_dataset: Optional[List[dict]] = None
        env_test_flag = os.getenv("TEST_FLAG")
        if test_mode is not None:
            self.test_mode = test_mode
        elif env_test_flag is None:
            self.test_mode = False
        else:
            self.test_mode = env_test_flag.strip().lower() not in {"", "0", "false", "no"}

    async def answer_user_question(self, utterance: str) -> str:
        """Return a synthesized answer based on reviews, inquiries, and detail sections."""

        snippets = self._collect_chunked_dataset_snippets(limit=100)

        if not snippets:
            section_tasks = [
                self._collect_section_snippets(
                    self.REVIEW_SECTION_SELECTORS, label="구매 후기", max_snippets=4
                ),
                self._collect_section_snippets(
                    self.INQUIRY_SECTION_SELECTORS, label="상품 문의", max_snippets=3
                ),
                self._collect_section_snippets(
                    self.DETAIL_SECTION_SELECTORS, label="상세 설명", max_snippets=2
                ),
                self._collect_section_snippets(
                    self.SPEC_SECTION_SELECTORS, label="상품 정보", max_snippets=2
                ),
            ]

            results = await asyncio.gather(*section_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                snippets.extend(result)

        if not snippets:
            return "관련 정보를 찾지 못했습니다. 다른 내용을 도와드릴까요?"

        llm = self._ensure_llm()
        if not llm:
            return "답변 생성 모델을 초기화하지 못했습니다. 잠시 후 다시 시도해 주시겠어요?"

        try:
            return llm.answer_product_question(
                utterance,
                snippets,
                language="ko",
            )
        except Exception as exc:  # noqa: BLE001
            return f"답변 생성 중 문제가 발생했습니다: {exc}"


    async def add_product_to_cart(self) -> str:
        """Click the add-to-cart button and confirm the action."""

        for selector in self.ADD_TO_CART_SELECTORS:
            try:
                button = self.page.locator(selector)
                if await button.count() == 0:
                    continue
                await button.first.click(timeout=self.search_timeout * 1000)
                await self._wait_for_cart_confirmation()
                return "장바구니에 담았습니다. 다른 필요한 게 있으신가요?"
            except PlaywrightTimeoutError:
                continue
        return "장바구니 버튼을 찾을 수 없었습니다. 직접 눌러 주시겠어요?"

    async def ask_for_preference_feedback(self) -> str:
        """Prompt the user for specific dissatisfaction feedback."""

        # In a full implementation this could trigger a new search with refined
        # keywords.  The Playwright layer simply prepares the prompt message.
        return "어떤 점이 마음에 안드시나요? 마음에 드는 물건을 추천해드릴게요."


    async def _collect_locator_text(self, locator: Locator) -> List[str]:
        """Extract text from the given locator, avoiding duplicates."""

        texts: List[str] = []
        element_handles = await locator.element_handles()
        for handle in element_handles:
            try:
                text = await handle.inner_text()
            except PlaywrightTimeoutError:
                continue
            if text:
                texts.append(text)
        return texts

    async def _wait_for_cart_confirmation(self) -> None:
        for selector in self.CART_CONFIRMATION_SELECTORS:
            try:
                await self.page.wait_for_selector(
                    selector,
                    timeout=int(self.search_timeout * 1000),
                    state="visible",
                )
                return
            except PlaywrightTimeoutError:
                continue


    def _normalize_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        return normalized.strip()

    def _collect_chunked_dataset_snippets(
        self,
        *,
        limit: int = 100,
        per_source_limit: int = 100,
    ) -> List[dict]:
        dataset = self._load_chunk_dataset()
        print(f"✓ 청크 데이터셋에서 {len(dataset)}개 청크 로드됨")
        print(f"✓ 최대 {limit}개 청크에서 대표 텍스트 추출 시도")
        print(f"✓ 출처별 최대 {per_source_limit}개 청크 허용됨")
        if not dataset:
            return []

        snippets: List[dict] = []
        per_source_counts: dict[str, int] = {}

        for chunk in dataset:
            if len(snippets) >= limit:
                break
            text = self._normalize_text(chunk.get("text_content") or "")
            if not text:
                continue
            source_type = (chunk.get("source_type") or "data").lower()
            if per_source_counts.get(source_type, 0) >= per_source_limit:
                continue

            snippets.append(
                {
                    "source": self._format_chunk_source(chunk),
                    "text": text,
                    "chunk_id": chunk.get("chunk_id"),
                    "metadata": chunk.get("metadata"),
                }
            )
            per_source_counts[source_type] = per_source_counts.get(source_type, 0) + 1

        return snippets

    def _load_chunk_dataset(self) -> List[dict]:
        if self._chunk_dataset is not None:
            return self._chunk_dataset

        data = self._read_chunk_file(self.chunk_data_path)

        if data is None and self.test_mode:
            fallback_path = self._find_latest_chunk_file()
            if fallback_path and fallback_path != self.chunk_data_path:
                data = self._read_chunk_file(fallback_path)
                if data is not None:
                    self.chunk_data_path = fallback_path

        self._chunk_dataset = data or []
        return self._chunk_dataset

    def _format_chunk_source(self, chunk: dict) -> str:
        source_file = chunk.get("source_file") or "chunk"
        source_type = chunk.get("source_type") or "data"
        origin = (chunk.get("metadata") or {}).get("origin_field") or ""
        if origin:
            return f"{source_type}:{origin} ({source_file})"
        return f"{source_type} ({source_file})"

    def _read_chunk_file(self, path: Optional[Path]) -> Optional[List[dict]]:
        if not path or not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
        except Exception:  # noqa: BLE001
            return None

    def _find_latest_chunk_file(self) -> Optional[Path]:
        base = Path("outputs/scenario_runs")
        if not base.exists():
            return None
        candidates = list(base.glob("*/chunked_data_output.json"))
        if not candidates:
            return None
        try:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:  # noqa: BLE001
            return None
        return candidates[0]

    async def _collect_section_snippets(
        self,
        selectors: Sequence[str],
        *,
        label: str,
        max_snippets: int,
    ) -> List[dict]:
        """Collect representative text snippets from the given selectors."""

        snippets: List[dict] = []
        seen: set[str] = set()

        for selector in selectors:
            if len(snippets) >= max_snippets:
                break

            locator = self.page.locator(selector)
            try:
                if await locator.count() == 0:
                    continue
                texts = await self._collect_locator_text(locator)
            except PlaywrightTimeoutError:
                continue

            for text in texts:
                normalized = self._normalize_text(text)
                if not normalized or normalized in seen:
                    continue
                snippets.append({"source": label, "text": normalized})
                seen.add(normalized)
                if len(snippets) >= max_snippets:
                    break

        return snippets

    def _ensure_llm(self) -> Optional[ShoppingAssistantLLM]:
        if not self._llm_initialized:
            self._llm_initialized = True
            try:
                self._llm = ShoppingAssistantLLM()
            except Exception:  # noqa: BLE001
                self._llm = None
        return self._llm

    def set_chunk_data_path(self, chunk_data_path: Optional[str]) -> None:
        new_path = (
            Path(chunk_data_path).expanduser()
            if chunk_data_path
            else self.DEFAULT_CHUNK_DATA_PATH
        )
        if new_path == self.chunk_data_path:
            return
        self.chunk_data_path = new_path
        self._chunk_dataset = None






async def run_demo(
    url: str,
    *,
    initial_question: str = "알러지 있는 사람도 먹을 수 있대?",
    user_follow_up: str = "좋아, 장바구니 넣어줘",
    headless: bool = True,
) -> None:
    """Run the scripted dialog for manual verification.

    Parameters
    ----------
    url:
        Product page URL to open (must be accessible from the current
        environment).
    initial_question:
        The question to answer by inspecting reviews and inquiries.
    user_follow_up:
        The follow-up utterance.  Setting this to "맘에 안들어" will trigger the
        dissatisfaction branch.
    headless:
        Forwarded to Playwright's browser launcher for debugging convenience.
    """

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # browser = await p.chromium.launch(headless=headless)
        browser = await p.firefox.launch(headless=False)  # 또는 webkit
        page = await browser.new_page()
        await page.goto("https://www.coupang.com/", wait_until="domcontentloaded")
        print(await page.title())

        agent = CoupangProductAgent(page)
        system_answer = await agent.answer_user_question(initial_question)
        print(f"SYSTEM: {system_answer}")

        follow_up_response = None
        intent = None
        llm: Optional[ShoppingAssistantLLM] = None
        try:
            llm = ShoppingAssistantLLM()
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  의도 분류 LLM 초기화 실패: {exc}")

        if llm:
            try:
                conversation = [
                    {"role": "user", "content": initial_question},
                    {"role": "assistant", "content": system_answer},
                ]
                intent_result = llm.classify_intent(
                    user_follow_up,
                    conversation,
                    current_product_info=None,
                    artifact_summary=None,
                )
                intent = intent_result.get("intent")
                print(f"[intent] {intent} (confidence={intent_result.get('confidence', 0):.2f})")
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️  의도 분류에 실패했습니다: {exc}")

        if intent == "satisfied":
            follow_up_response = await agent.add_product_to_cart()
        elif intent == "dissatisfied":
            follow_up_response = await agent.ask_for_preference_feedback()
        elif intent == "question":
            follow_up_response = await agent.answer_user_question(user_follow_up)
        else:
            follow_up_response = "네, 궁금하신 점이 더 있다면 말씀해 주세요."

        print(f"SYSTEM(follow_up): {follow_up_response}")

        await browser.close()


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import argparse

    parser = argparse.ArgumentParser(description="Coupang product page agent demo")
    parser.add_argument("url", help="Coupang product detail URL")
    parser.add_argument(
        "--follow-up",
        dest="follow_up",
        default="좋아, 장바구니 넣어줘",
        help="Follow-up utterance (default: scenario A)",
    )
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--question",
        dest="question",
        default="알러지 있는 사람도 먹을 수 있대?",
        help="Initial question to ask",
    )

    args = parser.parse_args()
    asyncio.run(
        run_demo(
            url=args.url,
            initial_question=args.question,
            user_follow_up=args.follow_up,
            headless=args.headless,
        )
    )
