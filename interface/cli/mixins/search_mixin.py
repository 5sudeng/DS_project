"""Mixin for search functionality."""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SearchMixin:
    """Mixin for handling product search."""

    async def _start_with_search(self):
        """Start with a product search."""
        query = input("🔍 검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어를 입력해주세요.")
            await self._get_initial_product()
            return

        await self._perform_search(query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        """Perform a product search."""
        logger.info("Performing search query='%s'", query)
        try:
            results = await self.search_agent.search(query, max_results=5)
            self.state.search_results = results

            if not results:
                print("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")
                logger.info("No results returned for query='%s'", query)

        except Exception as e:  # noqa: BLE001
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
        loaded = await self._load_product(selected.url)
        if not loaded:
            print("⚠️  선택한 상품을 불러오지 못했습니다. 다른 상품을 선택해 주세요.")

    async def _load_current_page(self):
        """Hook after loading a page to present recommendation hint."""
        await super()._load_current_page()
        if self.state.search_results:
            print("   '추천' → 페이지 요약 및 추천 보기")

    async def _summarize_current_page(self):
        """Summarize current search page results."""
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
            follow_up = self.llm.generate_requery_question(
                augmented_query,
                self.preference_memory,
                self.state.conversation_history,
            )
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

    async def _prompt_sort_and_apply(self):
        options = {
            "1": "랭킹순",
            "2": "낮은가격순",
            "3": "높은가격순",
            "4": "판매량순",
            "5": "최신순",
            "6": "평점순",
        }
        sel = input(
            "정렬 번호를 말씀하거나 입력하세요 (1:랭킹순 2:낮은가격순 3:높은가격순 4:판매량순 5:최신순 6:평점순): "
        ).strip()
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
        results = await self.search_agent.navigate_to_url(
            chosen["href"],
            max_results=self.state.results_per_page * 10,
        )
        if results:
            self.state.current_search_query = chosen["title"]
            self.state.all_search_results = results
            self.state.search_results = results[: self.state.results_per_page]
            self.state.page_offset = len(self.state.search_results)
            print(f"✓ {len(results)}개 상품 발견")
        else:
            print("연관검색어 이동 결과가 없습니다.")
