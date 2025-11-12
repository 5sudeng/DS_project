"""Coupang search agent using Playwright."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import List, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


@dataclass
class SearchResult:
    """Represents a single search result from Coupang."""

    rank: int
    title: str
    price: str
    url: str
    rating: Optional[str] = None
    review_count: Optional[str] = None


class CoupangSearchAgent:
    """Agent for searching products on Coupang."""

    SEARCH_INPUT_SELECTORS = [
        "input#headerSearchKeyword",
        "input[name='q']",
        "input[type='search']",
        "input.search-input",
    ]

    SEARCH_BUTTON_SELECTORS = [
        "button.search-btn",
        "button[type='submit']",
        "button:has-text('검색')",
    ]

    PRODUCT_ITEM_SELECTORS = [
        "li.search-product",
        "li.baby-product",
        "li[id^='productItem']",
        "div.search-product-wrap",
    ]

    def __init__(self, page: Page, search_timeout: float = 5.0):
        self.page = page
        self.search_timeout = search_timeout

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search for products on Coupang and return top results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        print(f"\n🔍 검색 중: '{query}'")

        # Navigate to Coupang main page if not already there
        if "coupang.com" not in self.page.url:
            print("📡 쿠팡 메인 페이지로 이동 중...")
            await self.page.goto("https://www.coupang.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5)

        # Find and fill search input
        search_input = await self._find_search_input()
        if not search_input:
            raise RuntimeError("검색창을 찾을 수 없습니다")

        print(f"🔍 검색어 입력: '{query}'")
        await search_input.clear()
        await search_input.fill(query)
        await asyncio.sleep(0.5)

        # Submit search
        print("⏳ 검색 실행 중...")
        await search_input.press("Enter")

        # Wait for navigation with extended timeout
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=45000)
            print("⏳ 검색 결과 로딩 중...")
            await asyncio.sleep(3)  # Wait for JavaScript rendering
        except Exception as e:
            print(f"⚠️  페이지 로드 경고: {e}")
            # Continue anyway
            await asyncio.sleep(2)

        # Parse search results
        results = await self._parse_search_results(max_results)
        print(f"✓ {len(results)}개 상품 발견")
        return results

    async def _find_search_input(self):
        """Find the search input element using multiple selectors."""
        for selector in self.SEARCH_INPUT_SELECTORS:
            try:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    return locator.first
            except PlaywrightTimeoutError:
                continue
        return None

    async def _parse_search_results(self, max_results: int) -> List[SearchResult]:
        """Parse search results from the page."""
        results = []

        # Try different selectors for product items
        product_items = None
        for selector in self.PRODUCT_ITEM_SELECTORS:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                if count > 0:
                    product_items = locator
                    break
            except PlaywrightTimeoutError:
                continue

        if not product_items:
            # Fallback: try to find any product links
            return await self._parse_results_fallback(max_results)

        # Parse each product item
        count = min(await product_items.count(), max_results)
        for i in range(count):
            try:
                item = product_items.nth(i)
                result = await self._parse_product_item(item, i + 1)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"⚠️  상품 {i+1} 파싱 실패: {e}")
                continue

        return results

    async def _parse_product_item(self, item, rank: int) -> Optional[SearchResult]:
        """Parse a single product item."""
        try:
            # Extract title
            title_elem = item.locator("a.name, div.name, dd.descriptions-inner").first
            title = await title_elem.inner_text() if await title_elem.count() > 0 else "제목 없음"
            title = title.strip()

            # Extract URL
            link_elem = item.locator("a[href*='/vp/products/'], a[href*='/products/']").first
            if await link_elem.count() == 0:
                link_elem = item.locator("a").first
            url = await link_elem.get_attribute("href") if await link_elem.count() > 0 else ""
            if url and not url.startswith("http"):
                url = f"https://www.coupang.com{url}"

            # Extract price
            price_elem = item.locator("strong.price-value, em.sale, span.price").first
            price = await price_elem.inner_text() if await price_elem.count() > 0 else "가격 정보 없음"
            price = price.strip()

            # Extract rating (optional)
            rating_elem = item.locator("em.rating, span.rating-star").first
            rating = await rating_elem.inner_text() if await rating_elem.count() > 0 else None

            # Extract review count (optional)
            review_elem = item.locator("span.rating-total-count, em.rating-total-count").first
            review_count = await review_elem.inner_text() if await review_elem.count() > 0 else None

            return SearchResult(
                rank=rank,
                title=self._clean_text(title),
                price=price,
                url=url,
                rating=rating,
                review_count=review_count,
            )
        except Exception as e:
            print(f"⚠️  상품 파싱 중 오류: {e}")
            return None

    async def _parse_results_fallback(self, max_results: int) -> List[SearchResult]:
        """Fallback method to parse search results."""
        results = []
        links = self.page.locator("a[href*='/vp/products/'], a[href*='/products/']")
        count = min(await links.count(), max_results * 2)  # Get more to filter

        seen_urls = set()
        rank = 1

        for i in range(count):
            try:
                link = links.nth(i)
                url = await link.get_attribute("href")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                if not url.startswith("http"):
                    url = f"https://www.coupang.com{url}"

                # Try to get title from link text or nearby elements
                title = await link.inner_text()
                if not title or len(title.strip()) < 3:
                    continue

                results.append(
                    SearchResult(
                        rank=rank,
                        title=self._clean_text(title),
                        price="가격 확인 필요",
                        url=url,
                    )
                )
                rank += 1

                if len(results) >= max_results:
                    break

            except Exception:
                continue

        return results

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def format_results_for_display(self, results: List[SearchResult]) -> str:
        """Format search results for user display."""
        if not results:
            return "검색 결과가 없습니다."

        lines = ["\n📦 검색 결과:\n"]
        for result in results:
            lines.append(f"{result.rank}. {result.title}")
            lines.append(f"   가격: {result.price}")
            if result.rating:
                lines.append(f"   평점: {result.rating}")
            lines.append("")  # Empty line between results

        return "\n".join(lines)