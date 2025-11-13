"""Interactive shopping CLI with AI-powered conversation."""

from __future__ import annotations

import asyncio
import os
import sys
import logging
from typing import Any, Dict, Optional

from playwright.async_api import Browser, Page, async_playwright

from agent.coupang_playwright_agent import CoupangProductAgent
from agent.coupang_search_agent import CoupangSearchAgent
from agent.interactive_cli.artifacts import ProductArtifactCollector
from agent.interactive_cli.browser import BrowserSessionConfig, bootstrap_browser
from agent.interactive_cli.cookies import (
    build_cookie_header,
    load_cookie_text,
    parse_cookie_records,
)
from agent.interactive_cli.state import ConversationState
from agent.llm_utils import ShoppingAssistantLLM

logger = logging.getLogger(__name__)


class InteractiveShoppingCLI:
    """Interactive CLI for shopping with AI assistance."""

    def __init__(
        self,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        api_key: Optional[str] = None,
        run_dir: Optional[str] = None,
    ):
        self.headless = headless
        self.run_dir = run_dir
        self.state = ConversationState()
        self.llm = ShoppingAssistantLLM(api_key=api_key)

        # Playwright objects (initialized in run())
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.product_agent: Optional[CoupangProductAgent] = None
        self.search_agent: Optional[CoupangSearchAgent] = None
        self.cookie_text: Optional[str] = load_cookie_text(cookie_file)
        self.cookie_header_value: Optional[str] = build_cookie_header(self.cookie_text)
        self.cookie_records = parse_cookie_records(self.cookie_text)
        self.artifact_summary: Dict[str, Any] = {}
        self.data_collector = ProductArtifactCollector(
            run_dir=self.run_dir,
            cookie=self.cookie_header_value,
        )

    async def run(self):
        """Main entry point for the interactive CLI."""
        print("=" * 60)
        print("🛍️  쿠팡 쇼핑 도우미에 오신 것을 환영합니다!")
        print("=" * 60)
        logger.info("InteractiveShoppingCLI started (headless=%s, run_dir=%s)", self.headless, self.run_dir)

        async with async_playwright() as playwright:
            session = await bootstrap_browser(
                playwright,
                BrowserSessionConfig(
                    headless=self.headless,
                    cookie_header=self.cookie_header_value,
                    cookie_records=self.cookie_records,
                ),
            )
            self.browser = session.browser
            self.page = session.page

            if session.applied_cookie_count:
                print(f"✓ {session.applied_cookie_count}개의 쿠키 로드됨 (봇 방어 쿠키 포함)")
            elif self.cookie_text:
                print("⚠️  쿠키 파일을 읽었지만 적용 가능한 쿠키를 찾지 못했습니다.")

            self.product_agent = CoupangProductAgent(
                self.page,
                response_generator=self.llm,
            )
            self.search_agent = CoupangSearchAgent(self.page)
            logger.info("Browser session established; agents ready.")

            try:
                await self._conversation_loop()
            except KeyboardInterrupt:
                print("\n\n👋 쇼핑을 종료합니다. 감사합니다!")
            finally:
                await self.browser.close()

    async def _conversation_loop(self):
        """Main conversation loop."""
        # Step 1: Get initial product URL
        await self._get_initial_product()

        # Step 2: Conversation loop
        while True:
            user_input = input("\n💬 > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "종료", "끝"]:
                print("\n👋 쇼핑을 종료합니다. 감사합니다!")
                break

            self.state.add_message("user", user_input)

            try:
                await self._handle_user_input(user_input)
            except Exception as e:
                print(f"\n❌ 오류가 발생했습니다: {e}")
                print("다시 시도해주세요.")

    async def _get_initial_product(self):
        """Get the initial product URL from user."""
        while True:
            url = input("\n📦 상품 URL을 입력하세요 (또는 'search'로 검색 시작): ").strip()
            logger.info("Initial product input received: %s", url)

            if url.lower() == "search":
                await self._start_with_search()
                return

            # Accept various Coupang URL formats
            if "coupang.com" in url:
                await self._load_product(url)
                return
            else:
                print("❌ 올바른 쿠팡 URL을 입력해주세요. (예: https://www.coupang.com/... 또는 https://shop.coupang.com/...)")

    async def _start_with_search(self):
        """Start with a product search."""
        query = input("🔍 검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어를 입력해주세요.")
            await self._get_initial_product()
            return

        await self._perform_search(query)
        await self._select_from_search_results()

    async def _load_product(self, url: str):
        """Load a product page."""
        print(f"\n⏳ 상품 페이지를 불러오는 중...")
        logger.info("Attempting to load product page: %s", url)

        try:
            # First, try to navigate to Coupang homepage to establish connection
            try:
                print("📡 쿠팡 연결 확인 중...")
                await self.page.goto("https://www.coupang.com", timeout=10000)
                await asyncio.sleep(0.5)
                print("✓ 쿠팡 연결 성공")
            except Exception as e:
                print(f"⚠️  쿠팡 메인 페이지 연결 실패: {e}")
                print("상품 페이지로 직접 시도합니다...")

            # Try to load the product page with retries
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"시도 {attempt}/{max_retries}...")
                    response = await self.page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                    if response and response.status == 200:
                        print(f"✓ 페이지 로드 성공 (HTTP {response.status})")
                        break
                    elif response and response.status >= 400:
                        print(f"⚠️  HTTP {response.status} 오류 발생")
                        if attempt < max_retries:
                            print(f"재시도 중... ({attempt}/{max_retries})")
                            await asyncio.sleep(2)
                        else:
                            raise RuntimeError(f"페이지 로드 실패: HTTP {response.status}")
                    elif response is None:
                        raise RuntimeError("응답 없음 - 네트워크 연결 확인 필요")
                except Exception as e:
                    if attempt < max_retries:
                        print(f"⚠️  시도 {attempt} 실패: {str(e)[:100]}")
                        print(f"재시도 중...")
                        await asyncio.sleep(2)
                    else:
                        raise

            # Wait for JavaScript to render
            print("⏳ 페이지 렌더링 대기 중...")
            await asyncio.sleep(2)

            # Wait for key elements to be visible
            try:
                await self.page.wait_for_selector("body", timeout=5000)
            except:
                pass  # Continue even if selector not found

            # Check if page loaded successfully
            current_url = self.page.url
            page_content = await self.page.content()
            if "this site can't be reached" in page_content.lower():
                raise RuntimeError("페이지에 접근할 수 없습니다. 네트워크 연결을 확인해주세요.")

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
                    except:
                        continue

            # Fallback
            if not product_name or len(product_name) < 2:
                product_name = f"상품 ({current_url.split('/')[-1][:20]})"

            self.state.current_url = url
            self.state.current_product_name = product_name
            logger.info("Product ready current_url=%s product_name=%s", current_url, product_name)

            try:
                await self._collect_structured_data(current_url)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️  데이터 수집 중 오류가 발생했습니다: {exc}")
                logger.exception("Structured data collection raised from load: %s", exc)

            print(f"✓ 상품: {self.state.current_product_name}")
            print(f"   URL: {current_url}")
            print("\n❓ 무엇이 궁금하신가요? (예: 발볼 넓은 사람도 신을 수 있을까요?)")

        except Exception as e:
            print(f"\n❌ 페이지 로드 실패: {e}")
            print("다시 시도하시겠습니까? 다른 URL을 입력하거나 'exit'로 종료하세요.")
            logger.exception("Product page load failed: %s", e)
            raise

    async def _collect_structured_data(self, current_url: str) -> None:
        """Collect HTML/reviews/inquiries using the crawling stack."""

        print("\n🗂️  상품 데이터 수집 중...")
        logger.info("Collecting structured data for %s", current_url)
        try:
            result = await self.data_collector.collect(current_url)
        except ValueError as exc:
            print(f"⚠️  상품 ID를 추출하지 못해 데이터 수집을 건너뜁니다: {exc}")
            logger.warning("Product ID parse failed: %s", exc)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  데이터 수집 중 예기치 않은 오류가 발생했습니다: {exc}")
            logger.exception("Unexpected error during data collection: %s", exc)
            return

        self.artifact_summary = result.summary
        print(f"✓ 데이터 수집 완료: {result.paths.run_dir}")
        logger.info("Structured data stored under %s", result.paths.run_dir)

    async def _handle_user_input(self, user_input: str):
        """Handle user input based on current state."""
        logger.info("Handling user input: %s", user_input)

        # If waiting for clarification about dissatisfaction
        if self.state.waiting_for_clarification:
            logger.info("Awaiting clarification; routing response.")
            await self._handle_clarification_response(user_input)
            return

        # Check if user is selecting from search results
        if self.state.search_results:
            if user_input.isdigit():
                logger.info("User selecting search result index=%s", user_input)
                await self._select_search_result(int(user_input))
                return

        # Use LLM to classify intent
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
            artifact_summary=self.artifact_summary,
        )

        print(f"\n[의도 파악: {intent_result['intent']} (신뢰도: {intent_result['confidence']:.2f})]")
        logger.info(
            "Intent classification result intent=%s confidence=%.2f",
            intent_result["intent"],
            intent_result["confidence"],
        )

        intent = intent_result["intent"]

        if intent == "question":
            await self._handle_question(user_input)
        elif intent == "satisfied":
            await self._handle_satisfied()
        elif intent == "dissatisfied":
            await self._handle_dissatisfied(intent_result)
        else:
            response = intent_result.get("response_suggestion", "죄송합니다. 잘 이해하지 못했습니다. 다시 말씀해주시겠어요?")
            print(f"\n🤖 {response}")
            self.state.add_message("assistant", response)

    async def _handle_question(self, question: str):
        """Handle user question about the product."""
        print("\n⏳ 리뷰와 문의를 확인하는 중...")
        logger.info("Processing question intent: %s", question)

        answer = await self.product_agent.answer_user_question(question)
        print(f"\n🤖 {answer}")

        # Ask if user wants to add to cart
        follow_up = "\n\n💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)"
        print(follow_up)

        self.state.add_message("assistant", answer + follow_up)

    async def _handle_satisfied(self):
        """Handle when user is satisfied and wants to add to cart."""
        print("\n⏳ 장바구니에 담는 중...")
        logger.info("Processing satisfied intent (add to cart)")

        result = await self.product_agent.add_product_to_cart()
        print(f"\n🤖 {result}")
        self.state.add_message("assistant", result)

        print("\n💡 다른 상품을 더 찾아보시겠어요? (검색어 입력 또는 'exit'로 종료)")

    async def _handle_dissatisfied(self, intent_result: Dict):
        """Handle when user is dissatisfied with the product."""
        logger.info(
            "Processing dissatisfied intent has_specific_reason=%s",
            intent_result.get("has_specific_reason"),
        )

        if intent_result.get("has_specific_reason"):
            # User provided specific reason
            reason = intent_result["reason"]
            keywords = intent_result.get("keywords", [])

            print(f"\n🔍 이해했습니다: {reason}")
            print("새로운 상품을 찾아보겠습니다...")

            # Generate search query using LLM
            search_query = self.llm.generate_search_query(
                self.state.current_product_name,
                reason,
                keywords,
                self.state.conversation_history,
                artifact_summary=self.artifact_summary,
            )

            print(f"💡 검색어: '{search_query}'")
            await self._perform_search(search_query)
            await self._select_from_search_results()
            logger.info("Search triggered with query='%s'", search_query)

        else:
            # Need clarification from user
            clarification_msg = self.llm.ask_for_clarification(
                self.state.conversation_history,
                self.state.current_product_name,
                artifact_summary=self.artifact_summary,
            )

            print(f"\n🤖 {clarification_msg}")
            self.state.add_message("assistant", clarification_msg)
            self.state.waiting_for_clarification = True
            logger.info("Asked user for clarification regarding dissatisfaction.")

    async def _handle_clarification_response(self, user_input: str):
        """Handle user's response to clarification question."""
        self.state.waiting_for_clarification = False
        logger.info("Received clarification response: %s", user_input)

        # Re-classify with the new information
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
            artifact_summary=self.artifact_summary,
        )

        reason = intent_result.get("reason", user_input)
        keywords = intent_result.get("keywords", [])

        print(f"\n🔍 알겠습니다: {reason}")
        print("새로운 상품을 찾아보겠습니다...")

        search_query = self.llm.generate_search_query(
            self.state.current_product_name,
            reason,
            keywords,
            self.state.conversation_history,
            artifact_summary=self.artifact_summary,
        )

        print(f"💡 검색어: '{search_query}'")
        await self._perform_search(search_query)
        await self._select_from_search_results()
        logger.info("Search triggered from clarification with query='%s'", search_query)

    async def _perform_search(self, query: str):
        """Perform a product search."""
        logger.info("Performing search query='%s'", query)
        try:
            results = await self.search_agent.search(query, max_results=5)
            self.state.search_results = results

            if not results:
                print("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")
                logger.info("No results returned for query='%s'", query)

        except Exception as e:
            print(f"\n❌ 검색 중 오류 발생: {e}")
            self.state.search_results = []
            logger.exception("Search failed for query='%s': %s", query, e)

    async def _select_from_search_results(self):
        """Display search results and ask user to select."""
        if not self.state.search_results:
            return

        logger.info("Displaying %d search results", len(self.state.search_results))
        display_text = self.search_agent.format_results_for_display(self.state.search_results)
        print(display_text)
        print("🔢 원하는 상품의 번호를 입력하세요 (1-5):")

    async def _select_search_result(self, selection: int):
        """Handle user's selection from search results."""
        if not (1 <= selection <= len(self.state.search_results)):
            print(f"❌ 1부터 {len(self.state.search_results)} 사이의 번호를 입력해주세요.")
            return

        logger.info("User selected result index=%d", selection)
        selected = self.state.search_results[selection - 1]
        print(f"\n✓ 선택: {selected.title}")

        # Clear search results and load new product
        self.state.clear_search_results()
        await self._load_product(selected.url)


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Interactive shopping assistant with AI")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--cookie-file", help="Path to cookie file for authentication")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)", default="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")
    parser.add_argument(
        "--run-dir",
        help="Root directory to store collected product data (default: outputs/scenario_runs)",
    )

    args = parser.parse_args()

    # Check for API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key가 필요합니다.")
        print("환경 변수 OPENAI_API_KEY를 설정하거나 --api-key 옵션을 사용하세요.")
        sys.exit(1)

    cli = InteractiveShoppingCLI(
        headless=args.headless,
        cookie_file=args.cookie_file,
        api_key=api_key,
        run_dir=args.run_dir,
    )

    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
