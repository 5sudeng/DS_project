"""Voice-enabled variant of the interactive shopping CLI."""

from __future__ import annotations

import argparse
import asyncio
import builtins
from typing import Optional

from agent.interactive_shopping_cli import InteractiveShoppingCLI
from agent.llm_utils import PreferenceMemory
from voice_io import build_io_interface, microphone_available


class InteractiveVoiceShoppingCLI(InteractiveShoppingCLI):
    """Interactive shopping CLI with optional voice IO and LLM assist features."""

    def __init__(
        self,
        *,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        api_key: Optional[str] = None,
        run_dir: Optional[str] = None,
        voice_enabled: bool = False,
        visual_enabled: bool = True,
        voice_backend: str = "openai",
        keyboard_voice: bool = False,
        stt_model: Optional[str] = None,
        voice_input_enabled: bool = True,
        rtzr_client_id: Optional[str] = None,
        rtzr_client_secret: Optional[str] = None,
    ):
        super().__init__(
            headless=headless,
            cookie_file=cookie_file,
            api_key=api_key,
            run_dir=run_dir,
        )
        self.voice_enabled = voice_enabled
        self.visual_enabled = visual_enabled
        self.voice_backend = voice_backend
        self.keyboard_voice = keyboard_voice
        self.stt_model = stt_model
        self.voice_input_enabled = voice_input_enabled
        self.rtzr_client_id = rtzr_client_id
        self.rtzr_client_secret = rtzr_client_secret

        self.preference_memory = PreferenceMemory()
        self.io = build_io_interface(
            voice_enabled=self.voice_enabled,
            stt_backend=self.voice_backend,
            openai_api_key=self.api_key,
            stt_model=self.stt_model,
            use_keyboard_input=self.keyboard_voice,
            rtzr_client_id=self.rtzr_client_id,
            rtzr_client_secret=self.rtzr_client_secret,
        )

        self._orig_print = None
        self._orig_input = None

    async def run(self):
        if not self.voice_enabled:
            await super().run()
            return

        mic_ok = microphone_available()
        if not mic_ok and self.voice_input_enabled:
            print("⚠️  마이크를 감지하지 못했습니다. 텍스트 모드로 대체됩니다.")
            self.voice_enabled = False
            await super().run()
            return

        if self.visual_enabled:
            print("🔊 음성 출력 활성화.")
            if self.voice_input_enabled:
                print("🎙️ 음성 입력 활성화: 키보드 없이 바로 말씀하시면 됩니다.")
                if self.keyboard_voice:
                    print("⌨️  키보드 푸시투토크 모드: 안내 후 엔터를 눌러 음성 입력을 여세요.")
            else:
                print("✏️  음성 입력 비활성화: 키보드로 텍스트를 입력하세요.")

        # Patch print/input to route through voice + optional visual output
        self._orig_print = builtins.print
        self._orig_input = builtins.input

        def _patched_print(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            if self.visual_enabled:
                self._orig_print(*args, **kwargs)
            if self.voice_enabled and text.strip():
                try:
                    self.io.speak(text)
                except Exception:
                    pass

        def _patched_input(prompt: str = "") -> str:
            prompt_str = prompt or ""
            if self.voice_enabled and prompt_str:
                try:
                    self.io.speak(prompt_str)
                except Exception:
                    pass
            if self.voice_enabled and self.voice_input_enabled:
                attempt = 0
                max_attempts = 3
                while attempt < max_attempts:
                    if self.visual_enabled:
                        self._orig_print("🎤 음성 입력 대기 중...")
                    heard = self.io.listen()
                    if heard:
                        if self.visual_enabled:
                            self._orig_print(f"[Voice 입력] {heard}")
                        return heard
                    attempt += 1
                    if attempt < max_attempts and self.visual_enabled:
                        self._orig_print("🔁 음성이 감지되지 않았습니다. 다시 말씀해주세요.")
                # 음성 모드이지만 반복 실패: 키보드 푸시투토크 모드가 아니면 키보드로 폴백하지 않고 빈 값 반환
                if self.keyboard_voice and self.visual_enabled:
                    return self._orig_input(prompt)
                return ""
            if self.visual_enabled:
                return self._orig_input(prompt)
            return ""

        builtins.print = _patched_print
        builtins.input = _patched_input

        try:
            await super().run()
        finally:
            builtins.print = self._orig_print or print
            builtins.input = self._orig_input or input

    async def _conversation_loop(self):
        """Voice-first loop: skip initial product/search prompt and accept commands directly."""
        print("\n🗣️ 명령을 말씀하거나 입력해주세요. (예: '쿠팡 들어가줘', '검색 후드티', 'exit')")
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
            except Exception as e:  # noqa: BLE001
                print(f"\n❌ 오류가 발생했습니다: {e}")
                print("다시 시도해주세요.")
                logger.exception("Conversation loop error (voice-first)")

    async def _start_with_search(self):
        """Start search with prompt augmentation and optional re-query."""
        query = input("🔍 검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어를 입력해주세요.")
            await self._get_initial_product()
            return

        query = await self._maybe_augment_query(query)
        await self._perform_search(query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        await super()._perform_search(query)
        if self.state.search_results:
            print("   '추천' → 페이지 요약 및 추천 보기")

    async def _load_current_page(self):
        await super()._load_current_page()
        if self.state.search_results:
            print("   '추천' → 페이지 요약 및 추천 보기")

    async def _handle_user_input(self, user_input: str):
        # LLM 기반 액션 라우팅 (음성 명령 → URL 이동 등)
        try:
            action_plan = self.llm.map_voice_command_to_action(user_input)
        except Exception:
            action_plan = {"action": "none"}

        if action_plan.get("action") == "open_url" and action_plan.get("url"):
            target_url = action_plan["url"]
            try:
                print(f"📡 요청하신 사이트로 이동합니다: {target_url}")
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                self.state.current_url = self.page.url
                print("✅ 페이지에 접속했습니다.")
                # 쿠팡 메인으로 이동했으면 바로 검색 흐름으로 유도
                if "coupang.com" in target_url:
                    await self._start_with_search()
                return
            except Exception as exc:  # noqa: BLE001
                print(f"❌ 페이지 이동 중 오류: {exc}")
                # 계속해서 기본 플로우 진행

        if user_inㅇput.lower() in ["추천", "요약", "summary"]:
            await self._summarize_current_page()
            return
        await super()._handle_user_input(user_input)

    async def _handle_dissatisfied(self, intent_result):
        reason = intent_result.get("reason")
        if reason:
            self.preference_memory.remember(reason)
        await super()._handle_dissatisfied(intent_result)

    async def _summarize_current_page(self):
        if not self.state.all_search_results:
            print("요약할 검색 결과가 없습니다. 먼저 검색을 진행해주세요.")
            return
        try:
            summary = self.llm.summarize_products_for_user(
                self.state.all_search_results,
                self.preference_memory,
                top_n=5,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"요약 생성 중 오류: {exc}")
            return

        print("\n🧠 페이지 요약/추천:")
        print(summary)

    async def _maybe_augment_query(self, query: str) -> str:
        """Apply preference-based augmentation and optional re-query."""
        augmented_query = query
        try:
            result = self.llm.augment_user_query(query, self.preference_memory, self.state.conversation_history)
            augmented_query = result.get("query", query).strip() or query
            if result.get("augmented") and augmented_query != query:
                rationale = result.get("rationale", "")
                print(f"🧠 선호를 반영해 검색어를 보강했습니다: '{augmented_query}'")
                if rationale:
                    print(f"   이유: {rationale}")
        except Exception as exc:  # noqa: BLE001
            print(f"검색어 보강 중 오류가 발생했습니다: {exc}")

        # If still vague, ask a quick follow-up (Re-Query)
        try:
            follow_up = self.llm.generate_requery_question(augmented_query, self.preference_memory, self.state.conversation_history)
        except Exception:
            follow_up = ""

        if follow_up:
            answer = input(f"\n🤔 {follow_up} ").strip()
            if answer:
                self.preference_memory.remember(answer)
                augmented_query = f"{augmented_query} {answer}".strip()

        return augmented_query


async def main():
    parser = argparse.ArgumentParser(description="Voice-enabled interactive shopping assistant")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--cookie-file", help="Path to cookie file for authentication")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)",
                        default="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")
    parser.add_argument("--run-dir", help="Root directory to store collected product data")
    parser.add_argument("--voice", action="store_true", help="Enable voice input/output")
    parser.add_argument("--no-visual", action="store_true", help="Disable visual/text output (voice-only)")
    parser.add_argument(
        "--voice-backend",
        choices=["openai", "vosk", "rtzr"],
        default="openai",
        help="Select STT backend: openai whisper API or local vosk",
    )
    parser.add_argument(
        "--rtzr-client-id",
        default="MZdY1Ll2VlnN2OahP7h1",
        help="RTZR CLIENT_ID (env RTZR_CLIENT_ID 로도 설정 가능)",
    )
    parser.add_argument(
        "--rtzr-client-secret",
        default="Fiey1zKUa5bw3IuOwUj0eoyyiEE8bYkDIhbe_PFf",
        help="RTZR CLIENT_SECRET (env RTZR_CLIENT_SECRET 로도 설정 가능)",
    )
    parser.add_argument(
        "--text-input",
        action="store_true",
        help="Disable STT and use keyboard/text input while keeping voice output",
    )
    parser.add_argument(
        "--keyboard-voice",
        action="store_true",
        help="Push-to-talk style voice capture triggered by the Enter key",
    )
    parser.add_argument(
        "--stt-model",
        help="STT model name (for openai backend)",
    )

    args = parser.parse_args()

    cli = InteractiveVoiceShoppingCLI(
        headless=args.headless,
        cookie_file=args.cookie_file,
        api_key=args.api_key,
        run_dir=args.run_dir,
        voice_enabled=args.voice,
        visual_enabled=not args.no_visual,
        voice_backend=args.voice_backend,
        keyboard_voice=args.keyboard_voice,
        stt_model=args.stt_model,
        voice_input_enabled=not args.text_input,
        rtzr_client_id=args.rtzr_client_id,
        rtzr_client_secret=args.rtzr_client_secret,
    )

    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
