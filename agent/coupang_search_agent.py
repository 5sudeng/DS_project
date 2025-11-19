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

    SORT_BUTTON_SELECTORS = {
        "랭킹순": [
            "button[data-testid='sorter-tab-ranking']",
            "a:has-text('랭킹순')",
            "button:has-text('랭킹순')",
            "li:has-text('랭킹순')",
        ],
        "낮은가격순": [
            "button[data-testid='sorter-tab-priceAsc']",
            "a:has-text('낮은가격순')",
            "button:has-text('낮은가격순')",
            "li:has-text('낮은가격순')",
        ],
        "높은가격순": [
            "button[data-testid='sorter-tab-priceDesc']",
            "a:has-text('높은가격순')",
            "button:has-text('높은가격순')",
            "li:has-text('높은가격순')",
        ],
        "판매량순": [
            "button[data-testid='sorter-tab-saleCount']",
            "a:has-text('판매량순')",
            "button:has-text('판매량순')",
            "li:has-text('판매량순')",
        ],
        "최신순": [
            "button[data-testid='sorter-tab-latest']",
            "a:has-text('최신순')",
            "button:has-text('최신순')",
            "li:has-text('최신순')",
        ],
    }

    def __init__(self, page, search_timeout=5.0):
        self.page = page
        self.search_timeout = search_timeout

    async def apply_sort(self, sort_type):
        """Click the sort button in Coupang search results page."""
        selectors = self.SORT_BUTTON_SELECTORS.get(sort_type, self.SORT_BUTTON_SELECTORS["랭킹순"])
        print(f"⏳ '{sort_type}' 정렬 버튼 클릭 중...")
        for selector in selectors:
            try:
                button = self.page.locator(selector)
                if await button.count() > 0:
                    await button.first.click()
                    await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await asyncio.sleep(2)
                    print(f"✅ '{sort_type}' 정렬 적용 완료 (selector: {selector})")
                    return True
            except Exception as e:
                print(f"⚠️  정렬 버튼 클릭 오류: {e}")
        # Debug: print attempted selectors
        print(f"⚠️  '{sort_type}' 정렬 버튼을 찾을 수 없습니다. 시도한 selectors: {selectors}")
        # Try to print nearby sorter container text to help debugging
        likely_containers = [
            "div.sorter",
            "div.sorter-group",
            "ul.sorter",
            "div.filter-sorter",
            "div.sort-options",
        ]
        for cont in likely_containers:
            try:
                loc = self.page.locator(cont)
                if await loc.count() > 0:
                    text = await loc.first.inner_text()
                    snippet = text.strip()[:500]
                    print(f"정렬 컨테이너 '{cont}' 내용 (샘플): {snippet}")
                    break
            except Exception:
                continue
        return False
        return False

    async def _get_shipping_filter_state(self) -> str:
        """현재 배송비 토글 상태 확인 (포함/제외)."""
        try:
            # "배송비 포함" 버튼의 상태 확인 — 로드 지연을 고려해 재시도
            include_selector = "div.srp_deliveryFeeToggle__6HXTR:has(label:has-text('배송비 포함')) button"
            include_button = None
            for attempt in range(3):
                include_button = self.page.locator(include_selector)
                try:
                    count = await include_button.count()
                except Exception:
                    count = 0
                if count > 0:
                    break
                await asyncio.sleep(0.4)

            if include_button and await include_button.count() > 0:
                include_class = await include_button.first.get_attribute("class")
                include_aria = await include_button.first.get_attribute("aria-pressed")

                print(f"\n🔍 배송비 토글 상태 확인 (재시도={attempt+1}):")
                print(f"  포함 버튼 class: '{include_class}' | aria-pressed: '{include_aria}'")

                # 우선 class에서 srp_enabled로 판단
                if include_class and "srp_enabled" in include_class:
                    print(f"  ✓ srp_enabled 클래스 있음 → 배송비포함 (활성)")
                    return "배송비포함"
                # aria-pressed가 true면 포함으로 판단
                if include_aria and include_aria.lower() == "true":
                    print(f"  ✓ aria-pressed='true' → 배송비포함 (활성)")
                    return "배송비포함"

                # 위 두 조건이 아니면 배송비제외로 판단
                print(f"  ✗ 활성 표시 없음 → 배송비제외 (활성)")
                return "배송비제외"

            # 버튼을 찾을 수 없으면 기본값
            print(f"  ⚠️  배송비 포함 버튼을 찾을 수 없음 → 기본값: 배송비제외")
            return "배송비제외"

        except Exception as e:
            print(f"⚠️  배송비 상태 확인 중 오류: {e}")
            return "배송비제외"

    async def apply_shipping_filter(self, shipping_option: str) -> bool:
        """Apply shipping filter next to sort options (배송비 포함/제외 토글)."""
        # 정렬 옆의 배송비 필터 토글 - 배송비포함 또는 배송비제외만 가능
        # HTML 구조: <div class="srp_deliveryFeeToggleWrapper__mQTRF">
        #              <div class="srp_deliveryFeeToggle__6HXTR">
        #                <button></button>
        #                <label>배송비 포함</label>
        
        if shipping_option not in ["배송비포함", "배송비제외"]:
            print(f"❌ 알 수 없는 배송비 옵션: {shipping_option}")
            return False
        
        print(f"\n⏳ '{shipping_option}' 배송비 옵션을 적용하는 중...")
        
        # 현재 상태 확인
        current_state = await self._get_shipping_filter_state()
        print(f"📊 현재 배송비 상태: {current_state}")
        
        # 이미 원하는 상태면 클릭하지 않음
        if current_state == shipping_option:
            print(f"✅ '{shipping_option}' 배송비 옵션이 이미 적용되어 있습니다.")
            return True
        
        # 원하는 상태가 아니면 토글 클릭 (토글 버튼은 하나뿐이며 클릭 시 상태 전환)
        print(f"⏳ '{shipping_option}'로 변경하기 위해 토글 클릭 중...")

        selectors = [
            "div.srp_deliveryFeeToggle__6HXTR button",
            "div[class*='deliveryFeeToggle'] button",
        ]

        toggle_button = None
        used_selector = None
        for selector in selectors:
            try:
                btn = self.page.locator(selector)
                if await btn.count() > 0:
                    toggle_button = btn.first
                    used_selector = selector
                    break
            except Exception:
                continue

        if not toggle_button:
            print(f"⚠️  '{shipping_option}' 배송비 토글을 찾을 수 없습니다. 시도한 selectors: {selectors}")
            await self._debug_shipping_elements()
            return False

        # 클릭 후 상태가 바뀌었는지 재확인 (재시도 포함)
        for attempt in range(3):
            try:
                await toggle_button.click()
            except Exception as e:
                print(f"⚠️  Toggle 클릭 시 오류 (시도 {attempt+1}): {e}")
                await asyncio.sleep(0.5)
                continue

            # 기다렸다가 상태 재확인
            try:
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            await asyncio.sleep(1)

            new_state = await self._get_shipping_filter_state()
            print(f"  -> 클릭 후 상태 확인: {new_state}")
            if new_state == shipping_option:
                print(f"✅ '{shipping_option}' 배송비 토글 적용 완료 (selector: {used_selector})")
                return True

            print(f"  ⚠️ 상태가 아직 변경되지 않음 (시도 {attempt+1})")

        print(f"❌ '{shipping_option}' 배송비 토글 적용 실패 — 재시도 후에도 상태가 변경되지 않았습니다.")
        await self._debug_shipping_elements()
        return False

    async def _debug_shipping_elements(self):
        """디버깅용: 페이지에서 배송비 관련 요소 찾기."""
        try:
            print("\n🔍 배송비 관련 요소 검색 중...")
            
            # 다양한 방식으로 배송비 관련 요소 찾기
            debug_selectors = [
                "button",
                "label",
                "span",
                "div[class*='shipping']",
                "div[class*='delivery']",
                "div[class*='sort']",
                "div[class*='filter']",
            ]
            
            for sel in debug_selectors:
                elements = self.page.locator(sel)
                count = await elements.count()
                if count > 0 and count < 50:  # 너무 많으면 스킵
                    for i in range(min(count, 10)):  # 최대 10개만 확인
                        try:
                            text = await elements.nth(i).inner_text()
                            if "배송비" in text or "delivery" in text.lower() or "shipping" in text.lower():
                                class_name = await elements.nth(i).get_attribute("class")
                                data_testid = await elements.nth(i).get_attribute("data-testid")
                                print(f"  [{sel}] 텍스트: '{text[:50]}' | class: {class_name} | data-testid: {data_testid}")
                        except:
                            pass
        except Exception as e:
            print(f"  디버깅 중 오류: {e}")

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

    async def search_page(self, query: str, page_num: int = 1, max_results: int = 50) -> List[SearchResult]:
        """
        Search for products on a specific page of Coupang.
        
        Args:
            query: Search query string
            page_num: Page number (1-indexed)
            max_results: Maximum number of results to return per page
        
        Returns:
            List of SearchResult objects
        """
        print(f"\n🔍 검색 중: '{query}' (페이지 {page_num})")

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
            await asyncio.sleep(3)
        except Exception as e:
            print(f"⚠️  페이지 로드 경고: {e}")
            await asyncio.sleep(2)

        # Navigate to specific page if page_num > 1
        if page_num > 1:
            await self._navigate_to_page(page_num)

        # Parse search results
        results = await self._parse_search_results(max_results)
        print(f"✓ {len(results)}개 상품 발견")
        return results

    async def _navigate_to_page(self, page_num: int) -> None:
        """Navigate to a specific page in search results."""
        print(f"⏳ 페이지 {page_num}로 이동 중...")
        
        try:
            # Try to find pagination element
            # Coupang typically uses ?q=query&page=N format or pagination buttons
            current_url = self.page.url
            
            if "page=" in current_url:
                # URL already has page parameter, update it
                import re
                new_url = re.sub(r"page=\d+", f"page={page_num}", current_url)
            else:
                # Add page parameter
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}page={page_num}"
            
            await self.page.goto(new_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️  페이지 이동 중 오류: {e}")
            await asyncio.sleep(1)

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
