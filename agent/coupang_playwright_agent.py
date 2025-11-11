"""Playwright-based Coupang shopping assistant agent.

This module implements scenario logic for interacting with a Coupang product
page after navigation has already happened.  The agent supports the following
capabilities:

1. Answer follow-up questions about the product by inspecting review and Q&A
   text that is already loaded on the page.
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
import re
from dataclasses import dataclass
from typing import List, Sequence

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError


@dataclass
class TextMatch:
    """Lightweight container describing text found on the page."""

    source: str
    text: str


class CoupangProductAgent:
    """Playwright-driven helper that supports the product-page dialog."""

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

    KEYWORD_EXTRACTION = re.compile(r"[0-9A-Za-z가-힣]{2,}")

    def __init__(self, page: Page, *, search_timeout: float = 1.5) -> None:
        self.page = page
        self.search_timeout = search_timeout

    async def answer_user_question(self, utterance: str) -> str:
        """Return a synthesized answer based on reviews and inquiries.

        The agent extracts keywords from the utterance, collects matching
        snippets from the review and inquiry sections, and constructs a concise
        reply.  If no relevant information is discovered, a graceful fallback is
        returned.
        """

        keywords = self._extract_keywords(utterance)
        if not keywords:
            return "현재 페이지에서 관련 정보를 찾지 못했습니다. 다른 궁금한 점이 있으신가요?"

        review_matches = await self._collect_section_matches(
            self.REVIEW_SECTION_SELECTORS, keywords, label="구매 후기"
        )
        inquiry_matches = await self._collect_section_matches(
            self.INQUIRY_SECTION_SELECTORS, keywords, label="상품 문의"
        )

        matches = review_matches + inquiry_matches
        if not matches:
            return "관련된 구매 후기나 상품 문의를 찾지 못했습니다. 다른 정보를 확인해 드릴까요?"

        review_summary = self._build_review_summary(review_matches)
        inquiry_summary = self._build_inquiry_summary(inquiry_matches)
        return " ".join(filter(None, [review_summary, inquiry_summary])).strip()

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

    async def _collect_section_matches(
        self,
        selectors: Sequence[str],
        keywords: Sequence[str],
        *,
        label: str,
    ) -> List[TextMatch]:
        """Gather section snippets that contain any of ``keywords``."""

        seen: set[str] = set()
        matches: List[TextMatch] = []

        for selector in selectors:
            locator = self.page.locator(selector)
            if await locator.count() == 0:
                continue

            try:
                section_texts = await self._collect_locator_text(locator)
            except PlaywrightTimeoutError:
                continue

            for text in section_texts:
                normalized = self._normalize_text(text)
                if not normalized or normalized in seen:
                    continue
                if any(keyword in normalized for keyword in keywords):
                    matches.append(TextMatch(source=label, text=normalized))
                    seen.add(normalized)

        return matches

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

    def _extract_keywords(self, utterance: str) -> List[str]:
        candidates = self.KEYWORD_EXTRACTION.findall(utterance)
        return [token for token in candidates if len(token.strip()) >= 2]

    def _build_review_summary(self, matches: Sequence[TextMatch]) -> str:
        if not matches:
            return ""
        highlighted = [match.text for match in matches[:2]]
        summary = "구매 후기에서 "
        summary += " ".join(
            f"‘{self._shorten_text(text)}’" for text in highlighted
        )
        summary += " 등의 평가가 있었습니다."
        return summary

    def _build_inquiry_summary(self, matches: Sequence[TextMatch]) -> str:
        if not matches:
            return ""
        highlighted = [match.text for match in matches[:1]]
        summary = " 상품 문의에서는 "
        summary += " ".join(
            f"‘{self._shorten_text(text)}’" for text in highlighted
        )
        summary += " 라는 답변이 확인되었습니다."
        return summary

    def _shorten_text(self, text: str, max_length: int = 80) -> str:
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "…"

    def _normalize_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        return normalized.strip()


async def run_demo(
    url: str,
    *,
    initial_question: str = "발볼 넓은 사람도 신을 수 있대?",
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
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url)

        agent = CoupangProductAgent(page)
        system_answer = await agent.answer_user_question(initial_question)
        print(f"SYSTEM: {system_answer}")

        if "장바구니" in user_follow_up:
            confirmation = await agent.add_product_to_cart()
            print(f"SYSTEM: {confirmation}")
        elif "맘에 안" in user_follow_up:
            prompt = await agent.ask_for_preference_feedback()
            print(f"SYSTEM: {prompt}")
        else:
            print("SYSTEM: 네, 다른 도움도 필요하시면 말씀해주세요.")

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
        default="발볼 넓은 사람도 신을 수 있대?",
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
