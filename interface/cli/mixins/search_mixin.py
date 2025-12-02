"""Mixin for search functionality."""

import logging
import asyncio
import re

logger = logging.getLogger(__name__)

class SearchMixin:
    """Mixin for handling product search."""

    async def _output_results_summary(self, results):
        """Generate and output a concise LLM summary for given results.

        This replaces raw list output. Always called after any result change:
        initial search, next/prev items, page navigation, sort, shipping filter.
        """
        if not results:
            return
        # Generate summary via LLM (runs in thread to avoid blocking event loop)
        try:
            summary = await asyncio.to_thread(self.llm.summarize_search_results, results)
        except Exception as e:
            logger.error("Failed to summarize results: %s", e)
            self.io_output("요약 생성에 실패했습니다. 번호를 말씀해 선택하거나 '다음상품'이라 말씀해주세요.")
            return

        # Console print raw (may include emoji markers)
        self.console_print(f"\n{summary}\n")
        # Voice friendly cleanup
        if self.output_mode in ("voice", "both") and self.io:
            import re as _re
            clean = summary.replace("\n", ". ")
            # Keep Korean, word chars, common punctuation; replace others with space
            clean = _re.sub(r'[^\w\s,.;:%\d가-힣()_-]', ' ', clean)
            clean = _re.sub(r'\s+', ' ', clean).strip()
            for chunk in [c.strip() for c in clean.split('.') if c.strip()]:
                try:
                    self.io.speak(chunk)
                except Exception as e:
                    logger.error("TTS summary chunk failed: %s", e)
                    break

        # Navigation guidance (voice + text)
        should_show_guidance = not self.state.guidance_shown_for_page
        if should_show_guidance:
            guidance_parts = []
            guidance_parts.append("상품을 선택하시려면 번호를 말씀해주세요.")
            if self.state.page_offset < len(self.state.all_search_results):
                guidance_parts.append("다음 상품을 더 보시려면 다음상품이라고 말씀해주세요.")
            guidance_parts.append("다른 페이지로 이동하시려면 페이지라고 말씀해주세요.")
            guidance_parts.append("다른 검색을 하시려면 검색이라고 말씀해주세요.")
            guidance_text = " ".join(guidance_parts)
            self.io_output(guidance_text)
            if self.output_mode in ("voice", "both") and self.io:
                try:
                    self.io.speak(guidance_text)
                except Exception:
                    pass
            # Mark shown for this page
            self.state.guidance_shown_for_page = True

    async def _start_with_search(self):
        """Start with a product search."""
        self.io_output("검색어를 입력하세요: ")
        query = (self.io_input() or "").strip()
        if not query:
            self.io_output("검색어가 입력되지 않았습니다. 다시 검색어를 말씀해주세요.")
            await self._get_initial_product()
            return

        await self._perform_search(query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        """Perform a product search (initial query)."""
        logger.info("Performing search query='%s'", query)
        self.io_output(f"\n검색 중: '{query}'")
        self.state.current_search_query = query
        self.state.current_page = 1
        self.state.page_offset = 0
        self.state.guidance_shown_for_page = False

        try:
            result = await self.search_agent.search(query, max_results=36)
        except Exception as e:
            logger.exception("Search execution failed: %s", e)
            self.io_output(f"검색 중 오류가 발생했습니다: {e}")
            return

        for w in result.warnings:
            self.io_output(f"⚠️ {w}")

        if not result.success:
            self.io_output(f"❌ 검색 실패: {result.error}")
            return

        from services.search_service import SearchResult
        converted = [
            SearchResult(
                rank=r.index,
                title=r.title,
                price=r.price,
                url=r.url,
                rating=r.rating
            ) for r in result.results
        ]
        self.state.all_search_results = converted
        first_batch = converted[:self.state.results_per_page]
        self.state.search_results = first_batch
        self.state.page_offset = len(first_batch)

        await self._output_results_summary(first_batch)
        self.io_output(f"원하는 상품 번호를 말씀해주세요 (1번부터 {len(first_batch)}번까지).")

    async def _select_from_search_results(self):
        """Guide user to select a result by number and load product.

        This method is referenced by IntentMixin. It listens for a numeric
        selection (1..len(self.state.search_results)) and loads that product.
        If the input is a non-number intent like '다음상품', it delegates back
        to the intent handler for natural language processing.
        """
        if not self.state.search_results:
            self.io_output("현재 선택 가능한 상품이 없습니다. 먼저 검색을 진행해주세요.")
            return

        self.io_output("번호를 말씀하시거나, '다음상품', '이전', '페이지', '검색' 중 하나를 말씀해주세요.")
        user_response = (self.io_input() or "").strip()
        if not user_response:
            return
        # Try to parse a number like "1", "1번"
        import re as _re
        m = _re.search(r"^(\d+)(번)?$", user_response)
        if m:
            idx = int(m.group(1))
            await self._select_search_result(idx)
            return
        # Delegate non-numeric intents
        if hasattr(self, '_handle_user_input'):
            await self._handle_user_input(user_response)

    async def _select_search_result(self, selection: int):
        """Handle user's selection from search results."""
        if not (1 <= selection <= len(self.state.search_results)):
            ### TODO
            self.io_output(f" 1부터 {len(self.state.search_results)} 사이의 번호를 입력해주세요.")
            return

        logger.info("User selected result index=%d", selection)
        selected = self.state.search_results[selection - 1]
        self.io_output(f"{selection}번 상품, {selected.title}를 선택하셨습니다. 상품 페이지를 불러오고 있습니다.")

        # Clear search results and load new product
        self.state.clear_search_results()
        loaded = await self._load_product(selected.url)
        if not loaded:
            self.io_output("선택한 상품 페이지를 불러오지 못했습니다. 다른 상품을 선택해주시거나, 다시 시도해주세요.")

    async def _read_search_results(self, top_n: int):
        """Read out the top N search results from the current offset."""
        if not self.state.all_search_results:
            self.io_output("❌ 읽어드릴 검색 결과가 없습니다.")
            return

        # 페이지 내 현재 오프셋부터 top_n개 가져오기
        start_idx = self.state.page_offset
        end_idx = min(start_idx + top_n, len(self.state.all_search_results))
        
        if start_idx >= len(self.state.all_search_results):
            self.io_output("⚠️ 더 이상 읽을 상품이 없습니다. 다음 페이지로 이동해볼까요?")
            return

        items = self.state.all_search_results[start_idx:end_idx]
        
        # Update current offset
        self.state.search_results = items
        self.state.page_offset = end_idx
        
        lines = [f"\n{start_idx + 1}번부터 {end_idx}번 상품:"]
        for idx, res in enumerate(items, start_idx + 1):
            lines.append(f"{idx}. {res.title}")
            lines.append(f"   가격: {res.price}")
            if res.rating:
                lines.append(f"   평점: {res.rating}")
            lines.append("")
        
        message = "\n".join(lines)
        self.io_output(message)
        
        if end_idx < len(self.state.all_search_results):
            self.io_output(f"\n💡 '다음 거 보여줘'라고 하면 {top_n}개를 더 보여드립니다.")
        else:
            self.io_output("\n💡 이 페이지의 모든 상품을 확인했습니다. '다음 페이지'로 이동할 수 있습니다.")

    async def _show_next_results(self, count: int = 3):
        """Show next N results in current page (offset-based navigation)."""
        if not self.state.current_search_query:
            self.io_output("❌ 진행 중인 검색이 없습니다.")
            return

        logger.info("User requesting next items in page %d for query='%s'",
                    self.state.current_page, self.state.current_search_query)

        # Calculate next offset in current page
        next_offset = self.state.page_offset + self.state.results_per_page

        # Check if there are more items in current page
        page_start = self.state.page_offset
        page_end = next_offset
        remaining_items = self.state.all_search_results[page_start:page_end]

        if remaining_items:
            display_items = remaining_items
            self.state.search_results = display_items
            await self._output_results_summary(display_items)
            self.state.page_offset = next_offset
            # Show options only once per page to reduce repetition
            if not self.state.guidance_shown_for_page:
                self.io_output("이 중에 마음에 드는 상품이 있으신가요?")
                has_previous = page_start > 0
                has_next = page_end < len(self.state.all_search_results)
                navigation_lines = [f"상품 번호를 입력하세요 (1번에서 {len(display_items)}번까지), 또는:"]
                if has_previous:
                    navigation_lines.append("   '이전' → 이전 상품 보기")
                if has_next:
                    navigation_lines.append("   '다음상품' → 다음 상품 보기")
                navigation_lines.append("   '페이지' → 다른 페이지로 이동")
                navigation_lines.append("   '검색' → 새로운 상품 검색")
                self.io_output("\n".join(navigation_lines))
                self.state.guidance_shown_for_page = True
        else:
            # No more items in current page
            self.io_output(f"\n✅ 페이지 {self.state.current_page}의 모든 상품을 확인했습니다.")
            # Reset guidance flag so we can show action guidance once
            self.state.guidance_shown_for_page = False
            await self._ask_page_navigation()

    async def _show_prev_results(self, count: int = 3):
        """Show previous N results in current page (offset-based navigation)."""
        if not self.state.current_search_query:
            self.io_output("❌ 진행 중인 검색이 없습니다.")
            return

        logger.info("User requesting previous items in page %d for query='%s'",
                    self.state.current_page, self.state.current_search_query)

        # page_offset points to the END of the current batch
        # To show previous batch: start = page_offset - 2 * results_per_page
        # end = page_offset - results_per_page
        previous_start = self.state.page_offset - 2 * self.state.results_per_page

        # Check if there are previous items
        if previous_start < 0:
            self.io_output("❌ 이전 상품이 없습니다.")
            return

        previous_end = previous_start + self.state.results_per_page
        page_start = previous_start
        page_end = previous_end
        previous_items = self.state.all_search_results[page_start:page_end]

        if previous_items:
            # Display previous items with 1-N numbering
            display_items = previous_items
            self.state.search_results = display_items

            await self._output_results_summary(display_items)
            # Update offset to point to end of previous batch (for consistent navigation)
            self.state.page_offset = previous_end
            # Check navigation options
            has_previous = previous_start > 0
            has_next = previous_end < len(self.state.all_search_results)

            # Ask if user likes any of these items
            self.io_output("이 중에 마음에 드는 상품이 있으신가요?")
            print_lines = [f"상품 번호를 입력하세요 (1번에서 {len(display_items)}번까지), 또는:"]
            if has_previous:
                print_lines.append("   '이전' → 더 이전의 5개 상품 보기")
            if has_next:
                print_lines.append("   '다음상품' → 다음 5개 상품 보기")
            print_lines.append("   '페이지' → 다른 페이지로 이동")
            print_lines.append("   '검색' → 새로운 상품 검색")
            self.io_output("\n".join(print_lines))
        else:
            self.io_output("❌ 이전 상품을 불러올 수 없습니다.")

    # 페이지 이동은 IntentMixin에서 메모리 내에서 처리하도록 위임

    async def _load_current_page(self):
        """Load products for the current page."""
        if not self.state.current_search_query:
            self.io_output("❌ 진행 중인 검색이 없습니다.")
            return

        try:
            self.io_output(f"\n페이지 {self.state.current_page} 로드 중...")
            
            # 실제 쿠팡 페이지 이동 (SearchService.go_to_page 사용)
            result = await self.search_agent.go_to_page(self.state.current_page)

            if not result.success:
                self.io_output(f"\n❌ {result.error}")
                # 페이지 이동 실패 시 이전 페이지로 복구
                self.state.current_page = max(1, self.state.current_page - 1)
                self.io_output(f"현재 페이지: {self.state.current_page}")
                return

            # 경고 메시지 출력
            for warning in result.warnings:
                self.io_output(f"✅ {warning}")

            if not result.results:
                self.io_output(f"\n😔 페이지 {self.state.current_page}에 상품이 없습니다.")
                self.state.current_page = max(1, self.state.current_page - 1)
                self.io_output(f"마지막 페이지는 {self.state.current_page}입니다.")
                return

            # Convert results
            from services.search_service import SearchResult
            converted_results = [
                SearchResult(
                    rank=r.index,
                    title=r.title,
                    price=r.price,
                    url=r.url,
                    rating=r.rating
                ) for r in result.results
            ]

            # 상태 업데이트
            self.state.all_search_results = converted_results
            self.state.page_offset = 0
            self.state.guidance_shown_for_page = False
            
            # 첫 배치 표시
            first_batch = self.state.all_search_results[:self.state.results_per_page]
            self.state.search_results = first_batch
            self.state.page_offset = len(first_batch)
            self.state.guidance_shown_for_page = False

            # Display first batch
            await self._display_current_results()

        except Exception as e:
            logger.exception("Error loading page %d: %s", self.state.current_page, e)
            self.io_output(f"\n❌ 페이지를 불러오는 중 오류 발생: {e}")

    async def _display_current_results(self):
        """Display current search results with navigation options."""
        if not self.state.search_results:
            return
        await self._output_results_summary(self.state.search_results)

    async def _handle_related_keywords(self):
        """Show related keywords."""
        self.io_output("🔍 연관 검색어를 찾고 있습니다...")
        keywords = await self.search_agent.get_related_keywords()
        
        if not keywords:
            self.io_output("⚠️ 연관 검색어를 찾지 못했습니다.")
            return

        lines = ["\n🔗 연관 검색어:"]
        for i, kw in enumerate(keywords[:5], 1):
            lines.append(f"{i}. {kw['title']}")
        
        self.io_output("\n".join(lines))
        self.io_output("\n💡 '1번 연관 검색어로 검색해줘'와 같이 말해보세요.")

    async def _select_related_keyword(self, keyword: str):
        """Select a related keyword to search."""
        # Check if keyword is an index (e.g. "1번")
        import re
        idx_match = re.search(r'(\d+)번', keyword)
        if idx_match:
            idx = int(idx_match.group(1))
            keywords = await self.search_agent.get_related_keywords()
            if 1 <= idx <= len(keywords):
                selected = keywords[idx-1]['title']
                self.io_output(f"✓ '{selected}'(으)로 검색합니다.")
                await self._perform_search(selected)
                await self._select_from_search_results()
                return

        # Otherwise treat as text
        self.io_output(f"✓ '{keyword}'(으)로 검색합니다.")
        await self._perform_search(keyword)
        await self._select_from_search_results()

    async def _ask_page_navigation(self):
        """Ask user to navigate: next page, specific page, previous page, or new search."""
        self.io_output(f"\n📄 현재 페이지: {self.state.current_page}")
        self.io_output("어떤 페이지로 이동하시겠어요?")
        self.io_output(f"   예: '다음 페이지', '2페이지', '이전 페이지', '검색'")

        user_response = (self.io_input() or "").strip()
        
        if not user_response:
            self.io_output("❌ 입력이 없습니다.")
            return
        
        # LLM을 통해 자연어 명령 처리
        from interface.cli.mixins.intent_mixin import IntentMixin
        if hasattr(self, '_handle_user_input'):
            await self._handle_user_input(user_response)
        else:
            # Fallback: 직접 처리
            self.io_output("❌ 명령을 처리할 수 없습니다.")
