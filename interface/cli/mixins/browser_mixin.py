"""Mixin for browser interactions and product loading."""

import asyncio
import logging
from typing import Optional

from services.browser_service import BrowserService
from services.search_service import SearchService

logger = logging.getLogger(__name__)

class BrowserMixin:
    """Mixin for handling browser interactions."""

    # async def _get_initial_product(self):
    #     """Get the initial product URL from user."""
    #     while True:
    #         ### voiceinput
    #         url = input("\n📦 상품 URL을 입력하세요 (또는 'search'로 검색 시작): ").strip().lstrip("\\")
    #         logger.info("Initial product input received: %s", url)

    #         if url.lower() == "search":
    #             await self._start_with_search()
    #             return

    #         # Accept various Coupang URL formats
    #         if "coupang.com" in url:
    #             loaded = await self._load_product(url)
    #             if loaded:
    #                 return
    #             self._io_output("❌ 상품을 불러오지 못했습니다. 다른 URL을 시도해 주세요.")
    #         else:
    #             self._io_output("❌ 올바른 쿠팡 URL을 입력해주세요. (예: https://www.coupang.com/... 또는 https://shop.coupang.com/...)")

    async def _load_product(self, url: str, *, _retry: bool = False) -> bool:
        """Load a product page (Legacy wrapper - calls workflow)."""
        return await self.load_product_workflow(url, _retry=_retry)

    async def load_product_workflow(self, url: str, *, _retry: bool = False) -> bool:
        """
        상품 로딩 워크플로우: 3단계로 구성
        1. 상품 상세 페이지 접속
        2. 상품 상세페이지 정보 수집
        3. 상품 요약 정보 생성
        """
        # Step 1: Navigate to product page
        navigation_success = await self._navigate_to_product(url, _retry=_retry)
        if not navigation_success:
            return False

        # Step 2: Collect product data
        collection_success = await self._collect_product_data()
        if not collection_success:
            ### TODO
            print("⚠️  상품 데이터를 수집하지 못해 다시 시도해야 합니다.")
            return False

        # Step 3: Generate product summary
        await self._generate_product_summary()
        
        ### TODO
        print("\n❓ 무엇이 궁금하신가요? (상품에 대해 질문해 주세요!)")
        return True

    async def _navigate_to_product(self, url: str, *, _retry: bool = False) -> bool:
        """
        Step 1: 상품 상세 페이지 접속
        
        Returns:
            bool: 페이지 접속 성공 여부
        """
        ### status
        print(f"\n⏳ 상품 페이지를 불러오는 중...")
        logger.info("Attempting to load product page: %s", url)

        try:
            # First, try to navigate to Coupang homepage to establish connection
            try:
                ### status
                print("📡 쿠팡 연결 확인 중...")
                await self.page.goto("https://www.coupang.com", timeout=10000)
                await asyncio.sleep(0.5)
                ### status
                print("✓ 쿠팡 연결 성공")
            except Exception as e:
                ### status
                print(f"⚠️  쿠팡 메인 페이지 연결 실패: {e}")
                ### status
                print("상품 페이지로 직접 시도합니다...")

            # Try to load the product page with retries
            max_retries = 3
            loaded = False
            for attempt in range(1, max_retries + 1):
                try:
                    ### status
                    print(f"시도 {attempt}/{max_retries}...")
                    response = await self.page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                    if response and response.status == 200:
                        ### status
                        print(f"✓ 페이지 로드 성공 (HTTP {response.status})")
                        loaded = True
                        break
                    elif response and response.status >= 400:
                        print(f"⚠️  HTTP {response.status} 오류 발생")
                        if attempt < max_retries:
                            print(f"재시도 중... ({attempt}/{max_retries})")
                            await asyncio.sleep(2)
                        else:
                            raise RuntimeError(f"페이지 로드 실패: HTTP {response.status}")
                    elif response is None:
                        ### status
                        raise RuntimeError("응답 없음 - 네트워크 연결 확인 필요")
                except Exception as e:
                    if attempt < max_retries:
                        ### status
                        print(f"⚠️  시도 {attempt} 실패: {str(e)[:100]}")
                        ### status
                        print(f"재시도 중...")
                        await asyncio.sleep(2)
                    else:
                        raise

            if not loaded:
                return False

            # Wait for JavaScript to render
            ### status
            print("⏳ 페이지 렌더링 대기 중...")
            await asyncio.sleep(2)

            # Wait for key elements to be visible
            try:
                await self.page.wait_for_selector("body", timeout=5000)
            except Exception:
                pass  # Continue even if selector not found

            current_url = self.page.url
            page_content = await self.page.content()
            if current_url.startswith("chrome-error://") or "this site can't be reached" in page_content.lower():
                logger.warning("Chrome error page loaded: %s", current_url)
                if not _retry and await self._recover_from_chrome_error(url):
                    return True
                return False
            if "coupang.com" not in current_url:
                logger.warning("Unexpected domain after navigation: %s", current_url)
                if not _retry and await self._recover_from_chrome_error(url):
                    return True
                return False

            # Extract product name from various sources
            title = await self.page.title()
            product_name = None

            # Try 1: Parse from title
            if title and len(title.strip()) > 0:
                product_name = title.split("|")[0].strip() if "|" in title else title.strip()

            # Try 2: Look for product name in common selectors
            if not product_name or product_name == "쿠팡!":
                selectors = [
                    "h1.prod-buy-header__title",
                    "h2.prod-buy-header__title",
                    "h1.product-title",
                    "h2.product-title",
                    ".product-name",
                    "[class*='product-title']",
                    "[class*='prod-title']",
                ]
                for selector in selectors:
                    try:
                        elem = self.page.locator(selector).first
                        if await elem.count() > 0:
                            product_name = await elem.inner_text()
                            product_name = product_name.strip()
                            if product_name:
                                break
                    except Exception:
                        continue

            # Fallback
            if not product_name or len(product_name) < 2:
                product_name = f"상품 ({current_url.split('/')[-1][:20]})"

            self.state.current_url = current_url
            self.state.current_product_name = product_name
            logger.info("Product ready current_url=%s product_name=%s", current_url, product_name)
            
            ### status
            print(f"✓ 상품: {self.state.current_product_name}")
            ### status
            print(f"   URL: {current_url}")
            return True

        except Exception as e:
            self._io_output(f"\n❌ 페이지 로드 실패: {e}")
            self._io_output("다시 시도하시겠습니까? 다른 URL을 입력하거나 'exit'로 종료하세요.")
            logger.exception("Product page load failed: %s", e)
            return False

    async def _collect_product_data(self) -> bool:
        """
        Step 2: 상품 상세페이지 정보 수집
        
        HTML, 리뷰, 문의, BTF 등 모든 구조화된 데이터 수집
        
        Returns:
            bool: 데이터 수집 성공 여부
        """
        if not self.state.current_url:
            logger.error("No current URL set for data collection")
            return False
        
        data_collected = await self._collect_structured_data(self.state.current_url)
        return data_collected

    async def _generate_product_summary(self) -> Optional[str]:
        """
        Step 3: 상품 요약 정보 생성
        
        수집된 데이터를 바탕으로 LLM을 사용하여 상품 요약 생성
        
        Returns:
            Optional[str]: 생성된 요약 문자열, 실패 시 None
        """
        ### TODO
        print("\n📝 상품 요약 정보를 생성하고 있습니다...")
        try:
            summary = self.llm.generate_product_summary(
                self.state.current_product_name,
                self.artifact_summary
            )
            ### status
            print("-" * 60)
            ### TODO
            print(summary)
            ### status
            print("-" * 60)
            return summary
        except Exception as e:
            logger.error("Failed to generate summary: %s", e)
            ### TODO
            print("⚠️  요약 정보를 생성하지 못했습니다.")
            return None


    async def _recover_from_chrome_error(self, url: str) -> bool:
        """Attempt to recover from chrome-error page by creating a fresh page."""
        if not self.browser:
            return False
        try:
            self._io_output("🔁 브라우저 탭을 새로 열어 다시 시도합니다...")
            context = self.page.context if self.page else None
            if self.page:
                try:
                    await self.page.close()
                except Exception:
                    logger.warning("Failed to close current page during recovery.")
            if context:
                self.page = await context.new_page()
            else:
                self.page = await self.browser.new_page()
            self.product_agent = BrowserService(self.page)
            self.search_agent = SearchService(self.page)
            return await self._load_product(url, _retry=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to recover from chrome error: %s", exc)
            return False

    async def _collect_structured_data(self, current_url: str) -> bool:
        """Collect HTML/reviews/inquiries using the crawling stack."""
        ### status
        print("\n🗂️  상품 데이터 수집 중...")
        logger.info("Collecting structured data for %s", current_url)
        
        # Get HTML from Playwright page (already loaded successfully)
        try:
            preloaded_html = await self.page.content()
            logger.info("Retrieved HTML from Playwright page (length: %d)", len(preloaded_html))
        except Exception as e:
            logger.warning("Failed to get page content from Playwright: %s", e)
            preloaded_html = None
        
        try:
            result = await self.data_collector.collect(current_url, preloaded_html=preloaded_html)
        except ValueError as exc:
            ### status
            print(f"⚠️  상품 ID를 추출하지 못해 데이터 수집을 건너뜁니다: {exc}")
            logger.warning("Product ID parse failed: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            ### status
            print(f"⚠️  데이터 수집 중 예기치 않은 오류가 발생했습니다: {exc}")
            logger.exception("Unexpected error during data collection: %s", exc)
            return False

        self.artifact_summary = result.summary
        if result.chunk_file and self.product_agent:
            self.product_agent.set_chunk_data_path(result.chunk_file)
        ### status
        print(f"✓ 데이터 수집 완료: {result.paths.run_dir}")
        logger.info("Structured data stored under %s", result.paths.run_dir)
        return True
