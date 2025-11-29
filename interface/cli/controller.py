"""Main controller for the Shopping CLI."""

from __future__ import annotations

import asyncio
import logging
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
from services.llm_service import PreferenceMemory, ShoppingLLMService

from interface.cli.mixins.browser_mixin import BrowserMixin
from interface.cli.mixins.search_mixin import SearchMixin
from interface.cli.mixins.intent_mixin import IntentMixin
from interface.cli.mixins.io_mixin import IOMixin

logger = logging.getLogger(__name__)


class ShoppingCLI(IOMixin, BrowserMixin, SearchMixin, IntentMixin):
    """Interactive CLI for shopping with AI assistance."""

    def __init__(
        self,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        api_key: Optional[str] = None,
        run_dir: Optional[str] = None,
        ocr_delay: float = 0.5,
        text_output_enabled: bool = True,
        voice_output_enabled: bool = False,
        text_input_enabled: bool = True,
        voice_input_enabled: bool = False,
        keyboard_voice: bool = False,
        voice_backend: str = "openai",
        voice_base_url: Optional[str] = None,
        voice_stt_model: Optional[str] = None,
        rtzr_client_id: Optional[str] = None,
        rtzr_client_secret: Optional[str] = None,
    ):
        super().__init__(
            text_output_enabled=text_output_enabled,
            voice_output_enabled=voice_output_enabled,
            text_input_enabled=text_input_enabled,
            voice_input_enabled=voice_input_enabled,
            keyboard_voice=keyboard_voice,
            voice_backend=voice_backend,
            voice_base_url=voice_base_url,
            voice_stt_model=voice_stt_model,
            rtzr_client_id=rtzr_client_id,
            rtzr_client_secret=rtzr_client_secret,
        )
        self.headless = headless
        self.run_dir = run_dir
        self.state = ConversationState()
        self.api_key = api_key
        self.llm = ShoppingLLMService(api_key=api_key)
        self.preference_memory = PreferenceMemory()
        self.ai_memory_enabled = False

        # Playwright objects (initialized in run())
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.product_agent: Optional[BrowserService] = None
        self.search_agent: Optional[SearchService] = None
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

    async def _run_cli(self):
        """Main entry point for the interactive CLI."""
        print("=" * 60)
        self._io_output("🛍️  쿠팡 쇼핑 도우미에 오신 것을 환영합니다!")
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

            self.product_agent = BrowserService(
                self.page,
                llm=self.llm,
            )
            self.search_agent = SearchService(self.page)
            logger.info("Browser session established; agents ready.")

            try:
                await self._conversation_loop()
            except KeyboardInterrupt:
                self._io_output("\n\n👋 쇼핑을 종료합니다. 감사합니다!")
            finally:
                await self.browser.close()

    async def _conversation_loop(self):
        """Main conversation loop."""
        # Step 1: Get initial product URL
        await self._ask_ai_memory_preference()

        # Step 2: Conversation loop
        while True:
            ### voiceinput
            user_input = input("\n💬 > ").strip()

            if not user_input:
                continue

            self.state.add_message("user", user_input)

            try:
                should_continue = await self._hanle_user_input(user_input)
                if not should_continue:
                    break
            except Exception as e:
                print(f"\n❌ 오류가 발생했습니다: {e}")
                print("다시 시도해주세요.")
