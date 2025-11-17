"""Voice-controlled (or text-controlled) browser agent orchestration."""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from playwright.async_api import async_playwright

from .interactive_cli.browser import BrowserSessionConfig, bootstrap_browser
from .interactive_cli.cookies import (
    build_cookie_header,
    load_cookie_text,
    parse_cookie_records,
)
from .llm_utils import VoiceBrowserLLM
from .voice_actions import BrowserActionHandler
from .voice_io import SpeechInterface, TextInterface


class VoiceBrowserAgent:
    """Main orchestration class for the voice browser."""

    def __init__(
        self,
        *,
        headless: bool = False,
        api_key: Optional[str] = "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"
,
        llm_model: str = "gpt-4o-mini",
        speech_model: str = "gpt-4o-mini",
        keyboard_input: bool = False,
        text_mode: bool = False,
        cookie_file: Optional[str] = None,
    ):
        self.headless = headless
        self.keyboard_input = keyboard_input
        self.text_mode = text_mode
        self.io = (
            TextInterface()
            if text_mode
            else SpeechInterface(
                openai_api_key=api_key,
                stt_model=speech_model,
                use_keyboard_input=keyboard_input,
            )
        )
        self.llm = VoiceBrowserLLM(api_key=api_key, model=llm_model)
        self.action_handler = BrowserActionHandler(self.io, self.llm)
        self.cookie_text = load_cookie_text(cookie_file)
        self.cookie_header_value = build_cookie_header(self.cookie_text)
        self.cookie_records = parse_cookie_records(self.cookie_text)
        self.current_site: Optional[str] = None

    async def run(self):
        self.io.speak("Voice browser를 시작합니다.")
        async with async_playwright() as playwright:
            session = await bootstrap_browser(
                playwright,
                BrowserSessionConfig(
                    headless=self.headless,
                    cookie_header=self.cookie_header_value,
                    cookie_records=self.cookie_records,
                ),
            )
            browser = session.browser
            page = session.page

            if session.applied_cookie_count:
                self.io.speak(f"{session.applied_cookie_count}개의 쿠키를 적용했습니다.")

            if self.keyboard_input and not self.text_mode:
                print(
                    "\n[키보드 음성 모드] 안내: 음성 출력이 끝난 뒤 엔터를 눌러 입력을 열고, "
                    "명령을 입력한 뒤 다시 엔터를 눌러 입력을 닫아주세요."
                )

            try:
                while True:
                    prompt_msg = "명령을 말씀해주세요." if not self.text_mode else "명령을 입력해주세요."
                    self.io.speak(prompt_msg)
                    user_text = self.io.listen()
                    if not user_text:
                        self.io.speak("명령을 인식하지 못했습니다. 다시 말씀해주세요.")
                        continue

                    if self.text_mode and user_text.lower() in {"exit", "quit"}:
                        self.io.speak("브라우저 에이전트를 종료합니다.")
                        break

                    self.io.speak(f"들었습니다: {user_text}")

                    augmented = self.llm.augment_command(user_text)
                    if augmented != user_text:
                        self.io.speak(f"명령을 보완했습니다: {augmented}")

                    cmd = self.llm.parse_command(augmented, current_site=self.current_site)
                    action = cmd.get("action")
                    error = cmd.get("error")

                    if error == "invalid_json":
                        self.io.speak("명령을 이해하지 못했습니다. 다시 말씀해주세요.")
                        continue
                    if error == "llm_failure":
                        self.io.speak("명령 해석에 문제가 있습니다. 잠시 후 다시 시도해주세요.")
                        continue

                    await self.action_handler.handle(
                        action,
                        cmd,
                        page,
                        current_site=self.current_site,
                    )
                    self.current_site = page.url
            finally:
                await browser.close()


async def run_voice_browser(
    *,
    headless: bool = False,
    keyboard_input: bool = False,
    text_mode: bool = False,
    cookie_file: Optional[str] = None,
):
    agent = VoiceBrowserAgent(
        headless=headless,
        keyboard_input=keyboard_input,
        text_mode=text_mode,
        cookie_file=cookie_file,
    )
    await agent.run()


def main():
    keyboard_env = os.getenv("VOICE_BROWSER_KEYBOARD", "")
    keyboard_mode = keyboard_env.strip().lower() in {"1", "true", "yes", "on"}
    text_env = os.getenv("VOICE_BROWSER_TEXT", "")
    text_mode = text_env.strip().lower() in {"1", "true", "yes", "on"}
    cookie_file = os.getenv("VOICE_BROWSER_COOKIE")
    asyncio.run(
        run_voice_browser(
            keyboard_input=keyboard_mode,
            text_mode=text_mode,
            cookie_file=cookie_file,
        )
    )


if __name__ == "__main__":
    main()
