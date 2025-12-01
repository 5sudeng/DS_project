"""Coupang search agent using Playwright."""

from __future__ import annotations

import asyncio
import re
import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

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
            # Fallback: Use URL-based search
            logger.warning("Search input not found, using URL-based search")
            try:
                import urllib.parse
                encoded_query = urllib.parse.quote(query)
                search_url = f"https://www.coupang.com/np/search?q={encoded_query}"
                logger.info(f"Navigating to search URL: {search_url}")
                await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                warnings.append("검색창 대신 URL로 검색했습니다")
            except Exception as e:
                logger.error("URL-based search failed: %s", e)
                return SearchOperationResult(
                    success=False,
                    error="검색창을 찾을 수 없고 URL 검색도 실패했습니다",
                    query=query
                )
        else:
            # Normal search using input field
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
        results, total_found = await self._parse_search_results(max_results)
        logger.info("Found %d products (total: %d)", len(results), total_found)
        
        # Convert to SearchResultType for result_types
        result_list = [
            SearchResultType(
                index=r.rank,
                title=r.title,
                price=r.price,
                url=r.url,
                rating=r.rating
            ) for r in results[:max_results]
        ]
        
        return SearchOperationResult(
            success=True,
            results=result_list,
            query=query,
            total_count=total_found,
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
                    
                    # Re-parse results after sort (최대 36개)
                    results, _ = await self._parse_search_results(max_results=36)
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
        logger.info(f"Current shipping filter state: {current_state}, Desired: {shipping_option}")
        
        if current_state == shipping_option:
            logger.info(f"Already in desired state: {shipping_option}")
            # 이미 원하는 상태이므로 현재 결과 반환
            results, _ = await self._parse_search_results(max_results=36)
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
                warnings=[f"이미 '{shipping_option}' 상태입니다."]
            )

        # 토글 필요 - 여러 selector 시도
        logger.info(f"Toggling shipping filter from {current_state} to {shipping_option}")
        selectors = SELECTORS.get("shipping_filter", [])
        
        for selector in selectors:
            try:
                btn = self.page.locator(selector).first
                count = await btn.count()
                
                if count > 0:
                    # Check visibility
                    try:
                        is_visible = await btn.is_visible(timeout=3000)
                    except:
                        is_visible = False
                    
                    if is_visible:
                        logger.info(f"Found shipping filter button with selector: {selector}")
                        
                        # 토글 전 URL 저장
                        url_before = self.page.url
                        logger.info(f"URL before toggle: {url_before}")
                        
                        await btn.click()
                        logger.info("Clicked shipping filter toggle button")
                        
                        # URL 변경 대기 (쿠팡은 토글 시 URL이 변경됨)
                        await asyncio.sleep(1.5)
                        
                        # 상태 변경 확인 - 최대 3번 재시도
                        new_state = None
                        for attempt in range(3):
                            new_state = await self._get_shipping_filter_state()
                            url_after = self.page.url
                            logger.info(f"Attempt {attempt + 1}/3 - URL after toggle: {url_after}")
                            logger.info(f"Attempt {attempt + 1}/3 - State: {new_state}, Expected: {shipping_option}")
                            
                            if new_state == shipping_option:
                                logger.info(f"Successfully applied shipping filter: {shipping_option}")
                                
                                # 페이지 로드 대기
                                try:
                                    await self.page.wait_for_load_state("domcontentloaded", timeout=8000)
                                except:
                                    await asyncio.sleep(1.0)
                                
                                # Re-parse results (최대 36개)
                                results, _ = await self._parse_search_results(max_results=36)
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
                            
                            # 다음 시도 전 대기
                            if attempt < 2:
                                await asyncio.sleep(1.0)
                        
                        # 3번 재시도 후에도 실패
                        logger.warning(f"Filter state verification failed after 3 attempts.")
                        logger.warning(f"URL before: {url_before}")
                        logger.warning(f"URL after: {self.page.url}")
                        logger.warning(f"Last detected state: {new_state}, Expected: {shipping_option}")
                        return SearchOperationResult(
                            success=False, 
                            error=f"'{shipping_option}' 필터를 클릭했지만 상태가 변경되지 않았습니다. URL을 확인해주세요."
                        )
            except Exception as e:
                logger.warning("Shipping filter toggle failed with selector %s: %s", selector, e)
                continue

        return SearchOperationResult(success=False, error=f"'{shipping_option}' 필터 버튼을 찾을 수 없습니다.")
    
    async def go_to_next_page(self) -> SearchOperationResult:
        """Go to the next page of search results."""
        logger.info("Navigating to next page")
        
        # 현재 URL 저장 (필터/정렬 파라미터 확인용)
        current_url = self.page.url
        logger.info(f"Current URL before navigation: {current_url}")
        
        # Try multiple selectors for the "Next" button (ordered by specificity)
        next_selectors = [
            "a.Pagination_nextBtn__TUY5t",  # Current Coupang pagination button
            "a[data-page='next']",           # Data attribute selector
            "a[title='다음']",               # Title attribute (more specific)
            "a.btn-next", 
            "a.btn-page.next", 
            "button.btn-next",
            "a.search-pagination-next"
        ]
        
        for selector in next_selectors:
            try:
                btn = self.page.locator(selector).first  # Use .first to avoid strict mode violation
                if await btn.count() > 0:
                    # Check if visible
                    try:
                        is_visible = await btn.is_visible()
                    except:
                        is_visible = False
                    
                    if is_visible:
                        # Check if disabled
                        btn_class = await btn.get_attribute("class") or ""
                        btn_disabled = await btn.get_attribute("disabled")
                        
                        if btn_disabled or "disabled" in btn_class:
                            return SearchOperationResult(success=False, error="더 이상 다음 페이지가 없습니다.")
                            
                        await btn.click()
                        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                        await asyncio.sleep(2)
                        
                        # 이동 후 URL 확인
                        new_url = self.page.url
                        logger.info(f"New URL after navigation: {new_url}")
                        
                        # Re-parse results (최대 36개)
                        results, total = await self._parse_search_results(max_results=36)
                        
                        # Convert to SearchResultType
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
                            total_count=total,
                            warnings=["다음 페이지로 이동했습니다."]
                        )
            except Exception as e:
                logger.warning("Next page navigation failed with selector %s: %s", selector, e)
                continue
                
        return SearchOperationResult(success=False, error="다음 페이지 버튼을 찾을 수 없습니다.")

    async def go_to_prev_page(self) -> SearchOperationResult:
        """Go to the previous page of search results."""
        logger.info("Navigating to previous page")
        
        # 현재 URL 저장 (필터/정렬 파라미터 확인용)
        current_url = self.page.url
        logger.info(f"Current URL before navigation: {current_url}")
        
        # Try multiple selectors for the "Prev" button (ordered by specificity)
        prev_selectors = [
            "a.Pagination_prevBtn__TUY5t",  # Current Coupang pagination button
            "a[data-page='prev']",           # Data attribute selector
            "a[title='이전']",               # Title attribute (more specific)
            "a.btn-prev", 
            "a.btn-page.prev", 
            "button.btn-prev",
            "a.search-pagination-prev"
        ]
        
        for selector in prev_selectors:
            try:
                btn = self.page.locator(selector).first  # Use .first to avoid strict mode violation
                if await btn.count() > 0:
                    # Check if visible
                    try:
                        is_visible = await btn.is_visible()
                    except:
                        is_visible = False
                    
                    if is_visible:
                        # Check if disabled
                        btn_class = await btn.get_attribute("class") or ""
                        btn_disabled = await btn.get_attribute("disabled")
                        
                        if btn_disabled or "disabled" in btn_class:
                            return SearchOperationResult(success=False, error="더 이상 이전 페이지가 없습니다.")
                            
                        await btn.click()
                        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                        await asyncio.sleep(2)
                        
                        # 이동 후 URL 확인
                        new_url = self.page.url
                        logger.info(f"New URL after navigation: {new_url}")
                        
                        # Re-parse results (최대 36개)
                        results, total = await self._parse_search_results(max_results=36)
                        
                        # Convert to SearchResultType
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
                        total_count=total,
                        warnings=["이전 페이지로 이동했습니다."]
                    )
            except Exception as e:
                logger.warning("Prev page navigation failed with selector %s: %s", selector, e)
                continue
                
        return SearchOperationResult(success=False, error="이전 페이지 버튼을 찾을 수 없습니다.")

    async def go_to_page(self, page_num: int) -> SearchOperationResult:
        """Go to a specific page number."""
        logger.info("Navigating to page %d", page_num)
        
        # 현재 URL 저장 (필터/정렬 파라미터 확인용)
        current_url = self.page.url
        logger.info(f"Current URL before navigation: {current_url}")
        
        try:
            # Try to find the page link
            # Coupang pagination usually looks like: <a class="btn-page">1</a>
            page_link = self.page.locator(f"a:text-is('{page_num}')")
            
            if await page_link.count() > 0 and await page_link.is_visible():
                await page_link.first.click()
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                
                # 이동 후 URL 확인
                new_url = self.page.url
                logger.info(f"New URL after navigation: {new_url}")
                
                # Re-parse results (최대 36개)
                results, total = await self._parse_search_results(max_results=36)
                
                # Convert to SearchResultType
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
                    total_count=total,
                    warnings=[f"{page_num}페이지로 이동했습니다."]
                )
            else:
                # If page number is not visible, it might be out of current range
                # We can try URL manipulation as fallback
                current_url = self.page.url
                if "page=" in current_url:
                    import re
                    new_url = re.sub(r'page=\d+', f'page={page_num}', current_url)
                    await self.page.goto(new_url, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    
                    # Re-parse results (최대 36개)
                    results, total = await self._parse_search_results(max_results=36)
                    
                    # Convert to SearchResultType
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
                        total_count=total,
                        warnings=[f"{page_num}페이지로 이동했습니다 (URL 이동)."]
                    )
                
                return SearchOperationResult(success=False, error=f"{page_num}페이지 버튼을 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error("Failed to navigate to page %d: %s", page_num, e)
            return SearchOperationResult(success=False, error=f"{page_num}페이지 이동 중 오류가 발생했습니다.")

    async def _get_shipping_filter_state(self) -> str:
        """Check current shipping filter state by examining URL and DOM."""
        try:
            # 1순위: URL 파라미터 확인 (가장 신뢰할 수 있음)
            current_url = self.page.url
            logger.info(f"[State Check] Current URL: {current_url}")
            
            # deliveryToggle=true → 배송비포함, false/없음 → 배송비제외
            if "deliveryToggle=true" in current_url:
                logger.info("[State Check] Result: 배송비포함 (URL has deliveryToggle=true)")
                return "배송비포함"
            elif "deliveryToggle=false" in current_url:
                logger.info("[State Check] Result: 배송비제외 (URL has deliveryToggle=false)")
                return "배송비제외"
            
            # 2순위: DOM 속성 확인 (쿠팡 구조: button class="srp_enabled__K9ZLM" = 포함, class="" = 제외)
            selectors_to_check = [
                "div.srp_deliveryFeeToggle__6HXTR button",
                "button[data-testid='delivery-fee-toggle']",
                "div[class*='deliveryFeeToggle'] button",
            ]
            
            for selector in selectors_to_check:
                try:
                    btn = self.page.locator(selector).first
                    btn_count = await btn.count()
                    
                    if btn_count > 0:
                        logger.info(f"[State Check] Checking selector: {selector}")
                        
                        # 버튼 클래스 확인 (활성화 시 srp_enabled__K9ZLM 클래스 추가)
                        btn_class = await btn.get_attribute("class") or ""
                        logger.info(f"[State Check] button class: '{btn_class}'")
                        
                        # srp_enabled 클래스가 있으면 배송비 포함 상태
                        if "srp_enabled" in btn_class:
                            logger.info(f"[State Check] Result: 배송비포함 (button has srp_enabled class)")
                            return "배송비포함"
                        
                        # 클래스가 비어있으면 배송비 제외 상태
                        if not btn_class.strip():
                            logger.info(f"[State Check] Result: 배송비제외 (button class is empty)")
                            return "배송비제외"
                        
                        # 기타 활성화 키워드 확인 (폴백)
                        if any(keyword in btn_class.lower() for keyword in ["enabled", "checked", "active", "on"]):
                            logger.info(f"[State Check] Result: 배송비포함 (button class contains activation keyword)")
                            return "배송비포함"
                        
                except Exception as e:
                    logger.debug(f"Failed to check selector {selector}: {e}")
                    continue
            
            # 기본값: 배송비 제외
            logger.info("[State Check] Result: 배송비제외 (default)")
            return "배송비제외"
        except Exception as e:
            logger.warning(f"Error checking shipping filter state: {e}")
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
        logger.info(f"Current page URL: {self.page.url}")
        
        for selector in SELECTORS["search_input"]:
            try:
                logger.debug(f"Trying selector: {selector}")
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    logger.info(f"Found search input with selector: {selector}")
                    return locator.first
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        # Try to find any visible input that might be a search box
        logger.warning("Standard selectors failed, trying generic input search")
        try:
            all_inputs = self.page.locator("input[type='text'], input[type='search'], input:not([type])")
            count = await all_inputs.count()
            logger.info(f"Found {count} generic input elements")
            for i in range(min(count, 10)):  # Check first 10 inputs
                inp = all_inputs.nth(i)
                if await inp.is_visible():
                    placeholder = await inp.get_attribute("placeholder") or ""
                    if "검색" in placeholder or "search" in placeholder.lower():
                        logger.info(f"Found search input via placeholder: {placeholder}")
                        return inp
        except Exception as e:
            logger.error(f"Generic input search failed: {e}")
        
        logger.error("Could not find search input element")
        return None

    async def _parse_search_results(self, max_results: int) -> Tuple[List[SearchResult], int]:
        """Parse search results from the page."""
        results = []

        # Try different selectors for product items (실제 검색 결과만)
        product_items = None
        for selector in SELECTORS["product_item"]:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()
                if count > 0:
                    product_items = locator
                    logger.info(f"Found {count} products with selector: {selector}")
                    break
            except PlaywrightTimeoutError:
                continue

        if not product_items:
            # Fallback: try to find any product links
            logger.info("No product items found with primary selectors, using fallback")
            return await self._parse_results_fallback(max_results)

        # Parse each product item
        count = await product_items.count()
        for i in range(count):
            try:
                item = product_items.nth(i)
                
                # 광고/추천/특가 상품 필터링
                item_class = await item.get_attribute("class") or ""
                item_id = await item.get_attribute("id") or ""
                
                # 광고, 추천, 프로모션 상품 스킵
                if any(keyword in item_class.lower() for keyword in ["ad", "advertise", "recommend", "promotion", "banner"]):
                    logger.debug(f"Skipping ad/recommendation item {i+1}: class={item_class}")
                    continue
                
                if any(keyword in item_id.lower() for keyword in ["ad", "banner", "promotion"]):
                    logger.debug(f"Skipping ad/promotion item {i+1}: id={item_id}")
                    continue
                
                result = await self._parse_product_item(item, len(results) + 1)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning("Failed to parse product item %d: %s", i + 1, e)
                continue

        logger.info(f"Parsed {len(results)} valid search results (filtered from {count} items)")
        return results, len(results)  # Return actual parsed count, not raw count

    async def _parse_product_item(self, item, rank: int) -> Optional[SearchResult]:
        """Parse a single product item."""
        try:
            # 먼저 전체 텍스트로 광고/특가 필터링
            item_text = await item.inner_text() if await item.count() > 0 else ""
            item_text_lower = item_text.lower()
            
            # 광고, 특가, 프로모션 키워드 필터링
            ad_keywords = ["ad", "광고", "특가진행중", "특가", "쿠팡 광고", "와우할인가", "이벤트", "기획전"]
            if any(keyword in item_text_lower or keyword in item_text for keyword in ad_keywords):
                logger.debug(f"Skipping ad/promotion item: contains '{[k for k in ad_keywords if k in item_text_lower or k in item_text]}'")
                return None
            
            # Extract title
            title_elem = item.locator("a.name, div.name, dd.descriptions-inner").first
            title = await title_elem.inner_text() if await title_elem.count() > 0 else "제목 없음"
            title = title.strip()
            
            # 제목이 너무 짧거나 없으면 스킵 (광고/배너일 가능성)
            if len(title) < 3 or title == "제목 없음":
                logger.debug(f"Skipping item with invalid title: {title}")
                return None
            
            # 제목에서도 광고/특가 키워드 체크
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ["특가진행중", "광고", "ad"]):
                logger.debug(f"Skipping item with ad keyword in title: {title}")
                return None

            # Extract URL
            link_elem = item.locator("a[href*='/vp/products/'], a[href*='/products/']").first
            if await link_elem.count() == 0:
                link_elem = item.locator("a").first
            url = await link_elem.get_attribute("href") if await link_elem.count() > 0 else ""
            
            # URL 검증: 실제 상품 URL인지 확인
            if not url or not ("/vp/products/" in url or "/products/" in url):
                logger.debug(f"Skipping item with invalid URL: {url}")
                return None
                
            if url and not url.startswith("http"):
                url = f"https://www.coupang.com{url}"

            # Extract price
            price_elem = item.locator("div.custom-oos, strong.price-value, em.sale, span.price").first
            price = await price_elem.inner_text() if await price_elem.count() > 0 else "가격 정보 없음"
            price = price.strip()
            
            # 가격이 없으면 스킵
            if price == "가격 정보 없음":
                logger.debug(f"Skipping item without price: {title}")
                return None

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

    async def _parse_results_fallback(self, max_results: int) -> Tuple[List[SearchResult], int]:
        """Fallback method to parse search results."""
        results = []
        links = self.page.locator("a[href*='/vp/products/'], a[href*='/products/']")
        total_count = await links.count()
        count = min(total_count, max_results * 2)  # Get more to filter

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

        return results, total_count

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
