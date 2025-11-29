"""Main controller for the Shopping CLI."""

from __future__ import annotations

import asyncio
import builtins
import logging
from typing import Any, Dict, List, Optional

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
from services.llm_service import ShoppingLLMService, PreferenceMemory
from core.voice_io import build_io_interface, microphone_available

from interface.cli.mixins.browser_mixin import BrowserMixin
from interface.cli.mixins.search_mixin import SearchMixin
from interface.cli.mixins.intent_mixin import IntentMixin

logger = logging.getLogger(__name__)


class ShoppingCLI(BrowserMixin, SearchMixin, IntentMixin):
    """Interactive CLI for shopping with AI assistance."""

    def __init__(
        self,
        headless: bool = False,
        cookie_file: Optional[str] = None,
        api_key: Optional[str] = None,
        run_dir: Optional[str] = None,
        ocr_delay: float = 0.5,
        *,
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
        self.headless = headless
        self.run_dir = run_dir
        self.state = ConversationState()
        self.api_key = api_key
        self.llm = ShoppingLLMService(api_key=api_key)

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

        # Voice/AI memory features
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
        self.io = None
        self._orig_print = None
        self._orig_input = None

    async def run(self):
        """Main entry point for the interactive CLI."""
        print("=" * 60)
        print("🛍️  쿠팡 쇼핑 도우미에 오신 것을 환영합니다!")
        print("=" * 60)
        logger.info("InteractiveShoppingCLI started (headless=%s, run_dir=%s)", self.headless, self.run_dir)

        self._setup_voice_io()

        try:
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
                    if self.voice_enabled:
                        await self._conversation_loop_voice()
                    else:
                        await self._conversation_loop_text()
                except KeyboardInterrupt:
                    print("\n\n👋 쇼핑을 종료합니다. 감사합니다!")
                finally:
                    await self.browser.close()
        finally:
            self._restore_io()

    # ------------------------------------------------------------------
    # Voice/Text IO helpers
    # ------------------------------------------------------------------
    def _setup_voice_io(self):
        if not self.voice_enabled:
            return

        mic_ok = True
        if self.voice_input_enabled:
            mic_ok = microphone_available()
        if not mic_ok:
            print("⚠️  마이크를 감지하지 못했습니다. 텍스트 모드로 대체됩니다.")
            self.voice_enabled = False
            return

        self.io = build_io_interface(
            voice_enabled=self.voice_enabled,
            stt_backend=self.voice_backend,
            openai_api_key=self.api_key,
            stt_model=self.stt_model,
            use_keyboard_input=self.keyboard_voice,
            rtzr_client_id=self.rtzr_client_id,
            rtzr_client_secret=self.rtzr_client_secret,
        )

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
                if self.keyboard_voice and self.visual_enabled:
                    return self._orig_input(prompt)
                return ""
            if self.visual_enabled:
                return self._orig_input(prompt)
            return ""

        builtins.print = _patched_print
        builtins.input = _patched_input

        if self.visual_enabled:
            print("🔊 음성 출력 활성화.")
            if self.voice_input_enabled:
                print("🎙️ 음성 입력 활성화: 키보드 없이 바로 말씀하시면 됩니다.")
                if self.keyboard_voice:
                    print("⌨️  키보드 푸시투토크 모드: 안내 후 엔터를 눌러 음성 입력을 여세요.")
            else:
                print("✏️  음성 입력 비활성화: 키보드로 텍스트를 입력하세요.")

    def _restore_io(self):
        if self._orig_print:
            builtins.print = self._orig_print
        if self._orig_input:
            builtins.input = self._orig_input

    # ------------------------------------------------------------------
    # Conversation loops
    # ------------------------------------------------------------------
    async def _conversation_loop_text(self):
        """Main conversation loop (text-first)."""
        await self._get_initial_product()

        while True:
            user_input = input("\n💬 > ").strip()
            if not user_input:
                continue

            self.state.add_message("user", user_input)

            try:
                should_continue = await self._handle_user_input_text(user_input)
                if not should_continue:
                    break
            except Exception as e:  # noqa: BLE001
                print(f"\n❌ 오류가 발생했습니다: {e}")
                print("다시 시도해주세요.")

    async def _conversation_loop_voice(self):
        """Voice-first loop: accept commands directly."""
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
                should_continue = await self._handle_user_input_voice(user_input)
                if not should_continue:
                    break
            except Exception as e:  # noqa: BLE001
                print(f"\n❌ 오류가 발생했습니다: {e}")
                print("다시 시도해주세요.")
                logger.exception("Conversation loop error (voice-first)")

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------
    async def _handle_user_input_text(self, user_input: str) -> bool:
        """Delegate to the standard intent handler (text mode)."""
        return await IntentMixin._handle_user_input(self, user_input)

    async def _handle_user_input_voice(self, user_input: str) -> bool:
        """Voice-first intent handler that tries action mapping before intent classification."""
        try:
            plan = self.llm.map_voice_command_to_actions(user_input)
        except Exception:
            plan = {"actions": []}

        if plan.get("actions"):
            await self._execute_actions(plan["actions"])
            return True

        lower = user_input.lower()
        if lower in ["추천", "요약", "summary"]:
            await self._summarize_current_page()
            return True
        if lower.startswith("정렬"):
            await self._prompt_sort_and_apply()
            return True
        if "배송" in lower:
            await self._prompt_shipping_and_apply()
            return True
        if "연관" in lower or "similar" in lower:
            await self._show_related_keywords()
            return True

        if user_input.isdigit() and self.state.search_results:
            num = int(user_input)
            if 1 <= num <= len(self.state.search_results):
                await self._select_search_result(num)
                return True

        # Fallback to standard intent classification
        return await IntentMixin._handle_user_input(self, user_input)

    async def _handle_dissatisfied(self, intent_result: Dict):
        """Capture dissatisfaction reasons into preference memory, then delegate."""
        reason = intent_result.get("reason")
        if reason:
            self.preference_memory.remember(reason)
        await IntentMixin._handle_dissatisfied(self, intent_result)

    # ------------------------------------------------------------------
    # Search helpers (augmented)
    # ------------------------------------------------------------------
    async def _start_with_search(self):
        """Start with a product search (with optional query augmentation)."""
        query = input("🔍 검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어를 입력해주세요.")
            await self._get_initial_product()
            return

        query = await self._maybe_augment_query(query)
        await self._perform_search(query)

    async def _perform_search(self, query: str, page_num: int = 1):
        """검색만 수행 후 결과 표시."""
        self.state.current_search_query = query
        results = await self._search_only(query, page_num=page_num)
        if not results:
            print("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")
            return
        await self._display_results(results, page_num=page_num, query=query)
        await self._select_from_search_results()

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
            if getattr(result, "rating", None):
                lines.append(f"   평점: {result.rating}")
            lines.append("")
        print("\n".join(lines))
        print("   '정렬' 또는 '배송비' 명령으로 옵션을 적용할 수 있습니다.")
        print("   '추천' → 페이지 요약 및 추천 보기")

    # ------------------------------------------------------------------
    # AI memory helpers
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Summaries & actions
    # ------------------------------------------------------------------
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
                        if getattr(res, "rating", None):
                            lines.append(f"   평점: {res.rating}")
                        lines.append("")
                    print("\n".join(lines))
            elif act in ["similar_search", "related_keywords"]:
                await self._show_related_keywords()

    async def _apply_sort_option(self, results: List[Any], sort_type: str) -> List[Any]:
        """Apply a simple client-side sort using price text when possible."""
        def price_to_int(price: str) -> int:
            digits = "".join(ch for ch in price if ch.isdigit())
            return int(digits) if digits else 0

        if sort_type == "낮은가격순":
            return sorted(results, key=lambda r: price_to_int(getattr(r, "price", "")))
        if sort_type == "높은가격순":
            return sorted(results, key=lambda r: price_to_int(getattr(r, "price", "")), reverse=True)
        if sort_type == "평점순":
            def rating_to_float(val: Optional[str]) -> float:
                try:
                    return float(val)
                except Exception:
                    return 0.0
            return sorted(results, key=lambda r: rating_to_float(getattr(r, "rating", None)), reverse=True)
        # Default: no-op ordering
        return results

    async def _apply_shipping_filter(self, results: List[Any], shipping_option: str) -> List[Any]:
        """Placeholder shipping filter; returns original list."""
        # Shipping info not available in current SearchResult; simply acknowledge.
        print(f"ℹ️  현재 수집 데이터에 배송비 정보가 없어 '{shipping_option}' 필터는 표시용으로만 적용됩니다.")
        return results

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
