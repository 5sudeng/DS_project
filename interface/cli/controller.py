"""Main controller for the Shopping CLI."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import Browser, Page, async_playwright

from services.browser_service import BrowserService
from services.search_service import SearchService
from interface.artifacts import ProductArtifactCollector
from services.browser_setup import BrowserSessionConfig, bootstrap_browser
from core.cookies import (
    build_cookie_header,
    load_cookie_text,
    parse_cookie_records,
)
from core.state import ConversationState
from services.llm_service import ShoppingLLMService

from interface.cli.mixins.browser_mixin import BrowserMixin
from interface.cli.mixins.search_mixin import SearchMixin
from interface.cli.mixins.intent_mixin import IntentMixin
from interface.cli.mixins.io_mixin import IOMixin

logger = logging.getLogger(__name__)


class ShoppingCLI(BrowserMixin, SearchMixin, IntentMixin, IOMixin):
    """Interactive CLI for shopping with AI assistance."""

    def __init__(
        self,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        api_key: Optional[str] = None,
        run_dir: Optional[str] = None,
        ocr_delay: float = 0.5,
        input_mode: str = "voice",
        output_mode: str = "both",
        keyboard_voice: bool = False,
        stt_backend: str = "rtzr",
    ):
        self.headless = headless
        self.run_dir = run_dir
        self.state = ConversationState()
        self.api_key = api_key
        self.llm = ShoppingLLMService(api_key=api_key)
        
        # Initialize Mixins
        IntentMixin.__init__(self)
        IOMixin.__init__(
            self,
            input_mode=input_mode,
            output_mode=output_mode,
            keyboard_voice=keyboard_voice,
            voice_backend=stt_backend,
        )

        # Playwright objects (initialized in run())
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.product_agent: Optional[BrowserService] = None
        self.search_agent: Optional[SearchService] = None

        # Auto-detect cookie.txt if not specified
        if cookie_file is None and Path("cookie.txt").exists():
            logger.info("No cookie file specified, found 'cookie.txt' in current directory. Using it.")
            cookie_file = "cookie.txt"

        self.cookie_text: Optional[str] = load_cookie_text(cookie_file)
        self.cookie_header_value: Optional[str] = build_cookie_header(self.cookie_text)
        self.cookie_records = parse_cookie_records(self.cookie_text)
        self.artifact_summary: Dict[str, Any] = {}
        self.data_collector = ProductArtifactCollector(
            run_dir=self.run_dir,
            cookie=self.cookie_header_value,
            api_key=self.api_key,
            ocr_delay=ocr_delay,
        )

    async def run(self):
        """Main entry point for the interactive CLI."""
        self.setup_io_patching()
        
        ### status
        self.console_print("=" * 60)
        ### TODO
        self.io_output("쿠팡 쇼핑 도우미에 오신 것을 환영합니다. 음성으로 상품을 검색하고, 리뷰를 확인하고, 장바구니에 담을 수 있습니다. 편안하게 쇼핑하세요.")
        ### status
        self.console_print("=" * 60)
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
                self.io_output(f"{session.applied_cookie_count}개의 쿠키를 불러왔습니다. 로그인 정보가 저장되었습니다.")
            elif self.cookie_text:
                self.io_output("쿠키 파일을 찾았지만, 사용 가능한 쿠키가 없습니다. 로그인이 필요할 수 있습니다.")

            self.product_agent = BrowserService(
                self.page,
                llm=self.llm,
            )
            self.search_agent = SearchService(self.page)
            logger.info("Browser session established; agents ready.")

            try:
                await self._conversation_loop()
            except KeyboardInterrupt:
                self.io_output("쇼핑을 종료합니다. 이용해 주셔서 감사합니다. 즐거운 쇼핑 되세요!")
            finally:
                await self.browser.close()

    async def _conversation_loop(self):
        """Main conversation loop."""
        # Step 0: Ask for AI memory preference
        await self._ask_ai_memory_preference()

        # Step 1: Conversation loop
        while True:
            self.io_output("무엇을 도와드릴까요?")
            user_input = (self.io_input() or "").strip()

            if not user_input:
                continue

            self.state.add_message("user", user_input)

            try:
                should_continue = await self._handle_user_input(user_input)
                if not should_continue:
                    break
            except Exception as e:
                self.io_output(f"문제가 발생했습니다. 다시 시도해주세요. 오류 내용: {e}")
                ### TODO
                self.io_output("다시 시도해주세요.")
