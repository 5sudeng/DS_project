"""Mixin for browser interactions and product loading."""

import asyncio
import logging
from typing import Optional

from services.browser_service import BrowserService
from services.search_service import SearchService
from services.product_navigator import ProductNavigator
from services.product_info_parser import ProductInfoParser

logger = logging.getLogger(__name__)

class BrowserMixin:
    """Mixin for handling browser interactions."""

    async def _get_initial_product(self):
        """Get the initial product URL from user."""
        while True:
            self.io_output("\n📦 상품 URL을 입력하세요 (또는 'search'로 검색 시작): ")
            url = (self.io_input() or "").strip().lstrip("\\")
            logger.info("Initial product input received: %s", url)

            if url.lower() == "search":
                await self._start_with_search()
                return

            # Accept various Coupang URL formats
            if "coupang.com" in url:
                loaded = await self._load_product(url)
                if loaded:
                    return
                ### TODO
                self.io_output("❌ 상품을 불러오지 못했습니다. 다른 URL을 시도해 주세요.")
            else:
                ### TODO
                self.io_output("❌ 올바른 쿠팡 URL을 입력해주세요. (예: https://www.coupang.com/... 또는 https://shop.coupang.com/...)")

    async def _load_product(self, url: str, *, _retry: bool = False) -> bool:
        """Load a product page using navigator, parser, and data collector."""
        self.console_print(f"\n⏳ 상품 페이지를 불러오는 중...")
        logger.info("Attempting to load product page: %s", url)

        try:
            # Step 1: Navigate to product page
            navigator = ProductNavigator(self.page)
            nav_result = await navigator.navigate_to_product(url)
            
            # Display navigation warnings
            for warning in nav_result.warnings:
                self.console_print(f"⚠️  {warning}")
            
            # Handle navigation failure
            if not nav_result.success:
                logger.warning("Navigation failed: %s", nav_result.error)
                if not _retry and nav_result.error and "Chrome 오류" in nav_result.error:
                    if await self._recover_from_chrome_error(url):
                        return True
                self.io_output(f"\n❌ {nav_result.error}")
                return False
            
            current_url = nav_result.url
            
            # Step 2: Extract product information
            parser = ProductInfoParser(self.page)
            product_name = await parser.extract_product_name(fallback_url=current_url)
            
            # Update state
            self.state.current_url = current_url
            self.state.current_product_name = product_name
            logger.info("Product ready current_url=%s product_name=%s", current_url, product_name)
            
            # Step 3: Collect structured data
            data_collected = await self._collect_structured_data(current_url)
            if not data_collected:
                self.io_output("⚠️  상품 데이터를 수집하지 못해 다시 시도해야 합니다.")
                return False
            
            self.console_print(f"✓ 상품: {self.state.current_product_name}")
            self.console_print(f"   URL: {current_url}")

            # Step 4: Generate and display summary
            self.io_output("\n📝 상품 요약 정보를 생성하고 있습니다...")
            try:
                summary = self.llm.generate_product_summary(
                    self.state.current_product_name,
                    self.artifact_summary
                )
                self.console_print("-" * 60)
                self.io_output(summary)
                self.console_print("-" * 60)
            except Exception as e:
                logger.error("Failed to generate summary: %s", e)
                self.io_output("⚠️  요약 정보를 생성하지 못했습니다.")
            
            self.io_output("\n❓ 무엇이 궁금하신가요? (상품에 대해 질문해 주세요!)")
            return True

        except Exception as e:
            self.io_output(f"\n❌ 페이지 로드 실패: {e}")
            self.io_output("다시 시도하시겠습니까? 다른 URL을 입력하거나 'exit'로 종료하세요.")
            logger.exception("Product page load failed: %s", e)
            return False

    async def _recover_from_chrome_error(self, url: str) -> bool:
        """Attempt to recover from chrome-error page by creating a fresh page."""
        if not self.browser:
            return False
        try:
            ### TODO
            self.io_output("🔁 브라우저 탭을 새로 열어 다시 시도합니다...")
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
