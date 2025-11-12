"""Interactive shopping CLI with AI-powered conversation."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Browser, Page, async_playwright

from agent.coupang_playwright_agent import CoupangProductAgent
from agent.coupang_scenario_pipeline import ScenarioPaths, parse_product_identifiers
from agent.coupang_search_agent import CoupangSearchAgent, SearchResult
from agent.llm_utils import ShoppingAssistantLLM
from crawling.fetch_html import fetch_html as fetch_product_html
from crawling.review import fetch_reviews
from crawling.inquiries import fetch_inquiries
from crawling.quantity import fetch_quantity_info


@dataclass
class ConversationState:
    """Maintains the state of the shopping conversation."""

    current_url: Optional[str] = None
    current_product_name: Optional[str] = None
    search_results: List[SearchResult] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    waiting_for_clarification: bool = False

    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def clear_search_results(self):
        """Clear previous search results."""
        self.search_results = []


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
        self.cookie_file = cookie_file
        self.run_dir = run_dir
        self.state = ConversationState()
        self.llm = ShoppingAssistantLLM(api_key=api_key)

        # Playwright objects (initialized in run())
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.product_agent: Optional[CoupangProductAgent] = None
        self.search_agent: Optional[CoupangSearchAgent] = None
        self.cookie_text: Optional[str] = None
        self.cookie_header_value: Optional[str] = None
        self.product_paths: Optional[ScenarioPaths] = None
        self.product_id: Optional[str] = None
        self.item_id: Optional[str] = None
        self.vendor_item_id: Optional[str] = None
        self.artifact_summary: Dict[str, Any] = {}

        if self.cookie_file:
            cookie_path = Path(self.cookie_file).expanduser()
            if cookie_path.exists():
                self.cookie_text = cookie_path.read_text(encoding="utf-8").strip()
                self.cookie_header_value = self._build_cookie_header(self.cookie_text)

    async def run(self):
        """Main entry point for the interactive CLI."""
        print("=" * 60)
        print("🛍️  쿠팡 쇼핑 도우미에 오신 것을 환영합니다!")
        print("=" * 60)

        async with async_playwright() as playwright:
            # Launch browser with anti-detection settings
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--ignore-certificate-errors',
                ]
            )

            # Create context with realistic browser fingerprint
            extra_headers = {
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            if self.cookie_header_value:
                extra_headers['Cookie'] = self.cookie_header_value

            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                extra_http_headers=extra_headers,
            )

            # Load cookies if provided
            if self.cookie_text:
                await self._load_cookies(context)

            self.page = await context.new_page()

            # Add comprehensive anti-detection JavaScript
            await self.page.add_init_script("""
                // Override webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en']
                });

                // Override chrome runtime
                window.chrome = {
                    runtime: {}
                };

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            self.product_agent = CoupangProductAgent(self.page)
            self.search_agent = CoupangSearchAgent(self.page)

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

    async def _load_cookies(self, context):
        """Load cookies from text format."""
        if not self.cookie_text:
            return
        cookies: List[Dict[str, Any]] = []

        try:
            data = json.loads(self.cookie_text)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            cookies = [data]
        elif isinstance(data, list):
            cookies = [item for item in data if isinstance(item, dict)]

        if not cookies:
            # Parse cookies from semicolon-separated format
            for line in self.cookie_text.split(';'):
                line = line.strip()
                if '=' not in line:
                    continue
                name, value = line.split('=', 1)
                cookie_dict = {
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.coupang.com',
                    'path': '/',
                }
                # Special handling for secure cookies
                if name.strip() in ['_abck', 'bm_sz', 'bm_sv', 'ak_bmsc', 'bm_so']:
                    cookie_dict['secure'] = True
                    cookie_dict['httpOnly'] = True
                    cookie_dict['sameSite'] = 'None'
                cookies.append(cookie_dict)

        if cookies:
            await context.add_cookies(cookies)
            print(f"✓ {len(cookies)}개의 쿠키 로드됨 (봇 방어 쿠키 포함)")

    def _build_cookie_header(self, raw_cookie: str) -> Optional[str]:
        """Convert JSON cookie blobs into a standard Cookie header string."""
        if not raw_cookie:
            return None

        try:
            data = json.loads(raw_cookie)
        except json.JSONDecodeError:
            return raw_cookie.strip() or None

        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
        else:
            items = []

        parts = []
        for item in items:
            name = item.get("name")
            value = item.get("value")
            if not name or value is None:
                continue
            parts.append(f"{name}={value}")
        return "; ".join(parts) if parts else None

    async def _load_product(self, url: str):
        """Load a product page."""
        print(f"\n⏳ 상품 페이지를 불러오는 중...")

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

            try:
                await self._collect_structured_data(current_url)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️  데이터 수집 중 오류가 발생했습니다: {exc}")

            print(f"✓ 상품: {self.state.current_product_name}")
            print(f"   URL: {current_url}")
            print("\n❓ 무엇이 궁금하신가요? (예: 발볼 넓은 사람도 신을 수 있을까요?)")

        except Exception as e:
            print(f"\n❌ 페이지 로드 실패: {e}")
            print("다시 시도하시겠습니까? 다른 URL을 입력하거나 'exit'로 종료하세요.")
            raise

    async def _collect_structured_data(self, current_url: str) -> None:
        """Collect HTML/reviews/inquiries using the crawling stack."""

        try:
            product_id, item_id, vendor_item_id = parse_product_identifiers(current_url)
        except ValueError as exc:
            print(f"⚠️  상품 ID를 추출하지 못해 데이터 수집을 건너뜁니다: {exc}")
            return

        self.product_id = product_id
        self.item_id = item_id
        self.vendor_item_id = vendor_item_id
        self.product_paths = ScenarioPaths.build(self.run_dir, product_id)

        print(f"\n🗂️  상품 데이터 수집 중 (product_id={product_id})...")

        try:
            summary = await asyncio.to_thread(self._collect_structured_data_sync)
            self.artifact_summary = summary
            print(f"✓ 데이터 수집 완료: {self.product_paths.run_dir}")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  데이터 수집 중 예기치 않은 오류가 발생했습니다: {exc}")

    def _collect_structured_data_sync(self) -> Dict[str, Any]:
        """Blocking helper that mirrors coupang_scenario_pipeline collection logic."""

        if not self.product_paths or not self.product_id:
            return {}

        steps: List[Dict[str, Any]] = []

        def record(name: str, status: str, details: Dict[str, Any]) -> None:
            serialized = {
                k: (str(v) if isinstance(v, Path) else v) for k, v in details.items()
            }
            steps.append({"name": name, "status": status, "details": serialized})

        # HTML
        try:
            resp, soup, out_path = fetch_product_html(
                self.product_id,
                self.item_id or "",
                self.vendor_item_id or "",
                cookie=self.cookie_header_value,
                timeout=40,
                outdir=self.product_paths.html_dir,
            )
            self._update_ids_from_url(resp.url)
            record(
                "fetch_html",
                "success",
                {
                    "status": resp.status_code,
                    "url": resp.url,
                    "file": out_path,
                    "title": soup.title.text.strip() if soup.title else "",
                    "resolved_item_id": self.item_id,
                    "resolved_vendor_item_id": self.vendor_item_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_html", "error", {"error": str(exc)})

        # Reviews
        try:
            review_pages = 1
            review_page_size = 20
            page_records: List[Dict[str, Any]] = []
            for page_no in range(1, review_pages + 1):
                resp, data = fetch_reviews(
                    product_id=self.product_id,
                    vendor_item_id=self.vendor_item_id,
                    item_id=self.item_id,
                    cookie=self.cookie_header_value,
                    page=page_no,
                    size=review_page_size,
                    outdir=str(self.product_paths.reviews_dir),
                    retries=2,
                )
                page_records.append(
                    {
                        "page": page_no,
                        "status": resp.status_code,
                        "response_keys": list(data.keys()),
                    }
                )
            record(
                "fetch_reviews",
                "success",
                {"output_dir": self.product_paths.reviews_dir, "pages": page_records},
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_reviews", "error", {"error": str(exc)})

        # Inquiries
        try:
            resp, data = fetch_inquiries(
                product_id=self.product_id,
                page_no=1,
                cookie=self.cookie_header_value,
                item_id=self.item_id,
                vendor_item_id=self.vendor_item_id,
                outdir=str(self.product_paths.inquiries_dir),
                retries=2,
                is_preview=True,
            )
            record(
                "fetch_inquiries",
                "success",
                {
                    "output_dir": self.product_paths.inquiries_dir,
                    "status": resp.status_code,
                    "response_keys": list(data.keys()),
                    "page_no": 1,
                },
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_inquiries", "error", {"error": str(exc)})

        # Quantity (optional)
        if self.item_id and self.vendor_item_id:
            try:
                resp, data = fetch_quantity_info(
                    self.product_id,
                    self.item_id,
                    self.vendor_item_id,
                    cookie=self.cookie_header_value,
                    outdir=str(self.product_paths.quantity_dir),
                )
                record(
                    "fetch_quantity",
                    "success",
                    {
                        "status": resp.status_code,
                        "output_dir": self.product_paths.quantity_dir,
                        "keys": list(data.keys()),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                record("fetch_quantity", "error", {"error": str(exc)})
        else:
            record(
                "fetch_quantity",
                "skipped",
                {
                    "reason": "itemId 또는 vendorItemId가 없어 quantity 수집을 건너뜁니다.",
                },
            )

        summary = {
            "product_id": self.product_id,
            "item_id": self.item_id,
            "vendor_item_id": self.vendor_item_id,
            "paths": {
                "run_dir": str(self.product_paths.run_dir),
                "html_dir": str(self.product_paths.html_dir),
                "reviews_dir": str(self.product_paths.reviews_dir),
                "inquiries_dir": str(self.product_paths.inquiries_dir),
                "quantity_dir": str(self.product_paths.quantity_dir),
            },
            "steps": steps,
        }
        return summary

    def _update_ids_from_url(self, url: Optional[str]) -> None:
        if not url:
            return
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.item_id = self.item_id or (query.get("itemId") or [None])[0]
        self.vendor_item_id = self.vendor_item_id or (query.get("vendorItemId") or [None])[0]

    async def _handle_user_input(self, user_input: str):
        """Handle user input based on current state."""

        # If waiting for clarification about dissatisfaction
        if self.state.waiting_for_clarification:
            await self._handle_clarification_response(user_input)
            return

        # Check if user is selecting from search results
        if self.state.search_results:
            if user_input.isdigit():
                await self._select_search_result(int(user_input))
                return

        # Use LLM to classify intent
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
        )

        print(f"\n[의도 파악: {intent_result['intent']} (신뢰도: {intent_result['confidence']:.2f})]")

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

        answer = await self.product_agent.answer_user_question(question)
        print(f"\n🤖 {answer}")

        # Ask if user wants to add to cart
        follow_up = "\n\n💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)"
        print(follow_up)

        self.state.add_message("assistant", answer + follow_up)

    async def _handle_satisfied(self):
        """Handle when user is satisfied and wants to add to cart."""
        print("\n⏳ 장바구니에 담는 중...")

        result = await self.product_agent.add_product_to_cart()
        print(f"\n🤖 {result}")
        self.state.add_message("assistant", result)

        print("\n💡 다른 상품을 더 찾아보시겠어요? (검색어 입력 또는 'exit'로 종료)")

    async def _handle_dissatisfied(self, intent_result: Dict):
        """Handle when user is dissatisfied with the product."""

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
            )

            print(f"💡 검색어: '{search_query}'")
            await self._perform_search(search_query)
            await self._select_from_search_results()

        else:
            # Need clarification from user
            clarification_msg = self.llm.ask_for_clarification(
                self.state.conversation_history,
                self.state.current_product_name,
            )

            print(f"\n🤖 {clarification_msg}")
            self.state.add_message("assistant", clarification_msg)
            self.state.waiting_for_clarification = True

    async def _handle_clarification_response(self, user_input: str):
        """Handle user's response to clarification question."""
        self.state.waiting_for_clarification = False

        # Re-classify with the new information
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
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
        )

        print(f"💡 검색어: '{search_query}'")
        await self._perform_search(search_query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        """Perform a product search."""
        try:
            results = await self.search_agent.search(query, max_results=5)
            self.state.search_results = results

            if not results:
                print("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")

        except Exception as e:
            print(f"\n❌ 검색 중 오류 발생: {e}")
            self.state.search_results = []

    async def _select_from_search_results(self):
        """Display search results and ask user to select."""
        if not self.state.search_results:
            return

        display_text = self.search_agent.format_results_for_display(self.state.search_results)
        print(display_text)
        print("🔢 원하는 상품의 번호를 입력하세요 (1-5):")

    async def _select_search_result(self, selection: int):
        """Handle user's selection from search results."""
        if not (1 <= selection <= len(self.state.search_results)):
            print(f"❌ 1부터 {len(self.state.search_results)} 사이의 번호를 입력해주세요.")
            return

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
