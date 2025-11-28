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
        ai_memory_enabled: bool = False,
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
        self.ai_memory_enabled = ai_memory_enabled

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
            if self.voice_enabled:
                try:
                    self.io.speak(text.strip())
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
        await self._ask_ai_memory_preference()

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

    async def _perform_search(self, query: str):
        """검색만 수행 후 결과 표시."""
        self.state.current_search_query = query
        results = await self._search_o ㅂnly(query, page_num=1)
        if not results:
            print("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")
            return
        await self._display_results(results, page_num=1, query=query)

    async def _load_current_page(self):
        await super()._load_current_page()
        if self.state.search_results:
            print("   '추천' → 페이지 요약 및 추천 보기")

    async def _handle_user_input(self, user_input: str):
        """Voice-first intent handler that avoids 부모 클래스의 추가 프롬프트."""
        # 1) LLM → 액션 리스트 매핑
        try:
            plan = self.llm.map_voice_command_to_actions(user_input)
        except Exception:
            plan = {"actions": []}

        if plan.get("actions"):
            await self._execute_actions(plan["actions"])
            return

        lower = user_input.lower()
        # 2) 수동 명령 처리
        if lower in ["추천", "요약", "summary"]:
            await self._summarize_current_page()
            return
        if lower.startswith("정렬"):
            await self._prompt_sort_and_apply()
            return
        if "배송" in lower:
            await self._prompt_shipping_and_apply()
            return
        if "연관" in lower or "similar" in lower:
            await self._show_related_keywords()
            return

        # 3) 숫자 선택(검색 결과 선택)
        if user_input.isdigit() and self.state.search_results:
            num = int(user_input)
            if 1 <= num <= len(self.state.search_results):
                await self._select_search_result(num)
                return

        # 4) 기타는 안내만
        print("🤖 이해하지 못했습니다. 예) '후드티 검색', '정렬 낮은가격순', '추천' 등을 말씀해보세요.")

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
        if not self.ai_memory_enabled:
            return augmented_query
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

    async def _ask_ai_memory_preference(self):
        """Ask user whether to enable AI memory (preferences/augment/re-query)."""
        if self.ai_memory_enabled:
            return
        choice = input("🧠 AI 메모리(선호 반영/재질문) 기능을 켤까요? (예/아니오): ").strip().lower()
        if choice in ["예", "y", "yes"]:
            self.ai_memory_enabled = True
            print("✅ AI 메모리를 활성화했습니다.")
        else:
            print("🚫 AI 메모리를 비활성화한 채로 진행합니다.")

    async def _search_only(self, query: str, page_num: int = 1):
        """검색만 수행하고 결과 리스트 반환."""
        fetch_count = self.state.results_per_page * 10
        try:
            results = await self.search_agent.search_page(query, page_num=page_num, max_results=fetch_count)
            self.preference_memory.append_event(f"search_page: {query} (page {page_num})")
            return results
        except Exception as exc:  # noqa: BLE001
            print(f"\n❌ 검색 중 오류 발생: {exc}")
            return []

    async def _display_results(self, results, page_num: int, query: Optional[str] = None):
        """검색 결과를 상태에 반영하고 첫 페이지를 표시."""
        if query:
            self.state.current_search_query = query
        self.state.current_search_query = self.state.current_search_query or ""
        self.state.current_page = page_num
        self.state.page_offset = 0
        self.state.all_search_results = results
        first_batch = results[: self.state.results_per_page]
        self.state.search_results = first_batch
        self.state.page_offset = len(first_batch)

        lines = [f"\n📦 검색 결과 (페이지 {page_num}):\n"]
        for idx, result in enumerate(first_batch, 1):
            lines.append(f"{idx}. {result.title}")
            lines.append(f"   가격: {result.price}")
            if result.rating:
                lines.append(f"   평점: {result.rating}")
            lines.append("")
        print("\n".join(lines))
        print("   '정렬' 또는 '배송비' 명령으로 옵션을 적용할 수 있습니다.")
        print("   '추천' → 페이지 요약 및 추천 보기")

    async def _execute_actions(self, actions: List[Dict[str, Any]]):
        """Execute ordered actions produced by LLM mapping."""
        for action in actions:
            act = action.get("action")
            if act == "open_url":
                url = action.get("url")
                if not url:
                    continue
                try:
                    print(f"📡 요청하신 사이트로 이동합니다: {url}")
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    self.state.current_url = self.page.url
                    print("✅ 페이지에 접속했습니다.")
                except Exception as exc:  # noqa: BLE001
                    print(f"❌ 페이지 이동 중 오류: {exc}")
            elif act == "search_page":
                query = action.get("query")
                if not query:
                    continue
                if self.ai_memory_enabled:
                    query = await self._maybe_augment_query(query)
                self.state.current_search_query = query
                results = await self._search_only(query, page_num=1)
                if results:
                    await self._display_results(results, page_num=1, query=query)
            elif act == "apply_sort":
                sort_type = action.get("sort_type") or action.get("option")
                if sort_type and self.state.all_search_results:
                    sorted_results = await self._apply_sort_option(self.state.all_search_results, sort_type)
                    self.state.all_search_results = sorted_results
                    self.state.search_results = sorted_results[: self.state.results_per_page]
                    self.state.current_sort_option = sort_type
                    print(f"✅ '{sort_type}' 정렬을 적용했습니다.")
            elif act == "apply_shipping":
                shipping = action.get("shipping_option") or action.get("option")
                if shipping and self.state.all_search_results:
                    filtered = await self._apply_shipping_filter(self.state.all_search_results, shipping)
                    self.state.all_search_results = filtered
                    self.state.search_results = filtered[: self.state.results_per_page]
                    self.state.current_shipping_filter = shipping
                    print(f"✅ '{shipping}' 배송비 옵션을 적용했습니다.")
            elif act == "summarize":
                top_n = action.get("top_n", 3)
                if self.state.all_search_results:
                    summary = self.llm.summarize_products_for_user(
                        self.state.all_search_results,
                        self.preference_memory,
                        top_n=top_n,
                    )
                    print("\n🧠 요약/추천:")
                    print(summary)
            elif act == "read_results":
                top_n = action.get("top_n", self.state.results_per_page)
                if self.state.all_search_results:
                    items = self.state.all_search_results[:top_n]
                    lines = [f"\n📦 상위 {len(items)}개 상품:"]
                    for idx, res in enumerate(items, 1):
                        lines.append(f"{idx}. {res.title}")
                        lines.append(f"   가격: {res.price}")
                        if res.rating:
                            lines.append(f"   평점: {res.rating}")
                        lines.append("")
                    print("\n".join(lines))
            elif act in ["similar_search", "related_keywords"]:
                await self._show_related_keywords()

    async def _prompt_sort_and_apply(self):
        options = {
            "1": "랭킹순",
            "2": "낮은가격순",
            "3": "높은가격순",
            "4": "판매량순",
            "5": "최신순",
            "6": "평점순",
        }
        sel = input("정렬 번호를 말씀하거나 입력하세요 (1:랭킹순 2:낮은가격순 3:높은가격순 4:판매량순 5:최신순 6:평점순): ").strip()
        sort_type = options.get(sel, "랭킹순")
        if self.state.all_search_results:
            sorted_results = await self._apply_sort_option(self.state.all_search_results, sort_type)
            self.state.all_search_results = sorted_results
            self.state.search_results = sorted_results[: self.state.results_per_page]
            self.state.current_sort_option = sort_type
            print(f"✅ '{sort_type}' 정렬을 적용했습니다.")
        else:
            print("정렬할 검색 결과가 없습니다. 먼저 검색해주세요.")

    async def _prompt_shipping_and_apply(self):
        sel = input("배송비 옵션을 말씀하거나 입력하세요 (1:배송비포함 2:배송비제외): ").strip()
        shipping_map = {"1": "배송비포함", "2": "배송비제외"}
        shipping = shipping_map.get(sel, "배송비제외")
        if self.state.all_search_results:
            filtered = await self._apply_shipping_filter(self.state.all_search_results, shipping)
            self.state.all_search_results = filtered
            self.state.search_results = filtered[: self.state.results_per_page]
            self.state.current_shipping_filter = shipping
            print(f"✅ '{shipping}' 배송비 옵션을 적용했습니다.")
        else:
            print("배송비 옵션을 적용할 검색 결과가 없습니다. 먼저 검색해주세요.")

    async def _show_related_keywords(self):
        related = await self.search_agent.get_related_keywords()
        if not related:
            print("연관검색어가 없습니다.")
            return
        print("\n🔗 연관검색어 목록:")
        for idx, rk in enumerate(related, 1):
            print(f" {idx}. {rk['title']}")
        choice = input("선택 번호를 말씀하거나 입력하세요 (0=취소): ").strip()
        if not choice.isdigit():
            return
        num = int(choice)
        if num == 0 or num > len(related):
            return
        chosen = related[num - 1]
        print(f"🔁 연관검색어로 이동: {chosen['title']}")
        results = await self.search_agent.navigate_to_url(chosen["href"], max_results=self.state.results_per_page * 10)
        if results:
            self.state.current_search_query = chosen["title"]
            self.state.all_search_results = results
            self.state.search_results = results[: self.state.results_per_page]
            self.state.page_offset = len(self.state.search_results)
            print(f"✓ {len(results)}개 상품 발견")
        else:
            print("연관검색어 이동 결과가 없습니다.")


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
    parser.add_argument(
        "--ai-memory",
        action="store_true",
        help="Enable AI memory based prompt augmentation and re-query",
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
        ai_memory_enabled=args.ai_memory,
    )

    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
