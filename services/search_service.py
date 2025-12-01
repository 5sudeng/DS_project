"""Coupang search agent using Playwright."""

from __future__ import annotations

import asyncio
import re
import logging
import random
from dataclasses import dataclass
from typing import List, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config.selectors import SELECTORS
from services.result_types import SearchOperationResult, SearchResult as SearchResultType

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result from Coupang."""

    rank: int
    title: str
    price: str
    url: str
    rating: Optional[str] = None
    review_count: Optional[str] = None


class SearchService:
    """Agent for searching products on Coupang."""

    def __init__(self, page: Page, search_timeout: float = 5.0):
        self.page = page
        self.search_timeout = search_timeout

    async def search(self, query: str, max_results: int = 5) -> SearchOperationResult:
        """
        Search for products on Coupang and return top results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            SearchOperationResult with search results and status
        """
        warnings = []
        logger.info("Searching for query: '%s'", query)

        # Navigate to Coupang main page if not already there
        if "coupang.com" not in self.page.url:
            logger.info("Navigating to Coupang main page")
            try:
                await self.page.goto("https://www.coupang.com", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(1.5)
            except Exception as e:
                return SearchOperationResult(
                    success=False,
                    error=f"쿠팡 메인 페이지로 이동하지 못했습니다: {str(e)}",
                    query=query
                )

        # Find and fill search input
        search_input = await self._find_search_input()
        if not search_input:
            logger.error("Search input not found")
            return SearchOperationResult(
                success=False,
                error="검색창을 찾을 수 없습니다",
                query=query
            )

        await search_input.clear()
        # Human-like typing to avoid bot detection
        await search_input.press_sequentially(query, delay=random.randint(100, 200))
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Submit search
        await search_input.press("Enter")

        # Wait for navigation with extended timeout
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=45000)
            await asyncio.sleep(3)  # Wait for JavaScript rendering
        except Exception as e:
            warnings.append(f"페이지 로드 경고: {str(e)}")
            logger.warning("Page load warning: %s", e)
            # Continue anyway
            await asyncio.sleep(2)

        # Parse search results
        results = await self._parse_search_results(max_results)
        logger.info("Found %d products", len(results))
        
        # Convert to SearchResultType for result_types
        result_list = [
            SearchResultType(
                index=r.rank,
                title=r.title,
                price=r.price,
                url=r.url,
                rating=r.rating
            ) for r in results
        ]
        
        return SearchOperationResult(
            success=True,
            results=result_list,
            query=query,
            warnings=warnings
        )

    async def apply_sort(self, sort_type: str) -> SearchOperationResult:
        """Click the sort button in Coupang search results page."""
        sort_selectors = SELECTORS.get("sort_buttons", {}).get(sort_type, SELECTORS.get("sort_buttons", {}).get("랭킹순"))
        if not sort_selectors:
            return SearchOperationResult(success=False, error=f"지원하지 않는 정렬 방식입니다: {sort_type}")

        logger.info("Applying sort type: %s", sort_type)
        for selector in sort_selectors:
            try:
                button = self.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click()
                    await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await asyncio.sleep(2)
                    
                    # Re-parse results after sort
                    results = await self._parse_search_results(max_results=5)
                    result_list = [
                        SearchResultType(
                            index=r.rank,
                            title=r.title,
                            price=r.price,
                            url=r.url,
                            rating=r.rating
                        ) for r in results
                    ]
                    return SearchOperationResult(
                        success=True,
                        results=result_list,
                        warnings=[f"'{sort_type}' 정렬이 적용되었습니다."]
                    )
            except Exception as e:
                logger.warning("Sort button click failed for selector %s: %s", selector, e)
        
        return SearchOperationResult(success=False, error=f"'{sort_type}' 정렬 버튼을 찾을 수 없습니다.")

    async def apply_shipping_filter(self, shipping_option: str) -> SearchOperationResult:
        """Apply shipping filter (배송비 포함/제외)."""
        if shipping_option not in ["배송비포함", "배송비제외"]:
            return SearchOperationResult(success=False, error=f"알 수 없는 배송비 옵션: {shipping_option}")

        logger.info("Applying shipping filter: %s", shipping_option)
        
        # Check current state
        current_state = await self._get_shipping_filter_state()
        if current_state == shipping_option:
            return SearchOperationResult(
                success=True, 
                warnings=[f"이미 '{shipping_option}' 상태입니다."]
            )

        # Toggle filter
        selectors = SELECTORS.get("shipping_filter", [])
        for selector in selectors:
            try:
                btn = self.page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    await asyncio.sleep(1)
                    
                    # Verify state change
                    new_state = await self._get_shipping_filter_state()
                    if new_state == shipping_option:
                        # Re-parse results
                        results = await self._parse_search_results(max_results=5)
                        result_list = [
                            SearchResultType(
                                index=r.rank,
                                title=r.title,
                                price=r.price,
                                url=r.url,
                                rating=r.rating
                            ) for r in results
                        ]
                        return SearchOperationResult(
                            success=True,
                            results=result_list,
                            warnings=[f"'{shipping_option}' 필터가 적용되었습니다."]
                        )
            except Exception as e:
                logger.warning("Shipping filter toggle failed: %s", e)

        return SearchOperationResult(success=False, error=f"'{shipping_option}' 필터 적용에 실패했습니다.")

    async def _get_shipping_filter_state(self) -> str:
        """Check current shipping filter state."""
        try:
            include_selector = "div.srp_deliveryFeeToggle__6HXTR:has(label:has-text('배송비 포함')) button"
            include_button = self.page.locator(include_selector)
            
            if await include_button.count() > 0:
                include_class = await include_button.first.get_attribute("class")
                include_aria = await include_button.first.get_attribute("aria-pressed")
                
                if (include_class and "srp_enabled" in include_class) or \
                   (include_aria and include_aria.lower() == "true"):
                    return "배송비포함"
            
            return "배송비제외"
        except Exception:
            return "배송비제외"

    async def get_related_keywords(self) -> List[Dict[str, str]]:
        """Get related keywords from the page."""
        selectors = SELECTORS.get("related_keywords", [])
        results = []
        
        for sel in selectors:
            try:
                loc = self.page.locator(sel)
                count = await loc.count()
                if count == 0:
                    continue
                    
                for i in range(count):
                    a = loc.nth(i)
                    title = (await a.inner_text()).strip()
                    href = await a.get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            href = f"https://www.coupang.com{href}"
                        results.append({"title": title, "href": href})
                
                if results:
                    break
            except Exception:
                continue
                
        return results

    async def _find_search_input(self):
        """Find the search input element using multiple selectors."""
        for selector in SELECTORS["search_input"]:
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
        for selector in SELECTORS["product_item"]:
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
            logger.info("No product items found with primary selectors, using fallback")
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
                logger.warning("Failed to parse product item %d: %s", i + 1, e)
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
            price_elem = item.locator("div.custom-oos, strong.price-value, em.sale, span.price").first
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
            logger.warning("Error parsing product item: %s", e)
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

                # Try to find price from nearby elements or title
                price = "가격 확인 필요"
                
                # Method 1: Try to find price element in parent container (우선)
                try:
                    # Get parent container
                    parent = link.locator("xpath=ancestor::li[1] | xpath=ancestor::div[@class][1]").first
                    if await parent.count() > 0:
                        # Try various price selectors
                        price_selectors = [
                            "div.custom-oos",
                            "strong.price-value",
                            "em.sale",
                            "span.price",
                            "strong:has-text('원')",
                            "em:has-text('원')",
                            ".price:has-text('원')"
                        ]
                        for selector in price_selectors:
                            price_elem = parent.locator(selector).first
                            if await price_elem.count() > 0:
                                price_text = await price_elem.inner_text()
                                if price_text and '원' in price_text:
                                    price = price_text.strip()
                                    break
                except Exception:
                    pass
                
                # Method 2: Extract from title using regex (fallback)
                if price == "가격 확인 필요":
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})*원)', title)
                    if price_match:
                        # Get the last occurrence (usually the sale price)
                        all_prices = re.findall(r'\d{1,3}(?:,\d{3})*원', title)
                        if all_prices:
                            price = all_prices[-1]  # Use last price (sale price)

                results.append(
                    SearchResult(
                        rank=rank,
                        title=self._clean_text(title),
                        price=price,
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
