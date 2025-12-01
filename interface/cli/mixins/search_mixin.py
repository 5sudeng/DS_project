"""Mixin for search functionality."""

import logging
import asyncio
import re

logger = logging.getLogger(__name__)

class SearchMixin:
    """Mixin for handling product search."""

    async def _start_with_search(self):
        """Start with a product search."""
        self.io_output("어떤 상품을 찾으시나요? 검색어를 말씀해주세요.")
        query = (self.io_input() or "").strip()
        if not query:
            self.io_output("검색어가 입력되지 않았습니다. 다시 검색어를 말씀해주세요.")
            await self._get_initial_product()
            return

        await self._perform_search(query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        """Perform a product search."""
        logger.info("Performing search query='%s'", query)
        self.io_output(f"{query}를 검색하고 있습니다. 잠시만 기다려 주세요.")
        
        try:
            # 페이지 내 최대 36개 상품만 가져오기
            result = await self.search_agent.search(query, max_results=36)
            
            # Handle warnings
            for warning in result.warnings:
                self.console_print(f"⚠️  {warning}")
            
            if not result.success:
                self.io_output(f"검색에 실패했습니다. {result.error}. 다른 검색어로 다시 시도해주세요.")
                self.state.clear_search_results()
                logger.error("Search failed for query='%s': %s", query, result.error)
                return
            
            # Convert SearchResultType back to SearchResult for compatibility
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
            
            # 상태 초기화 (새 검색)
            self.state.current_search_query = query
            self.state.current_page = 1
            self.state.page_offset = 0
            self.state.all_search_results = converted_results
            self.state.current_sort_option = None
            self.state.current_shipping_filter = None
            
            total_count = result.total_count or len(converted_results)
            self.io_output(f"검색이 완료되었습니다. 총 {total_count}개의 상품을 찾았습니다.")

            if not converted_results:
                self.io_output("검색 결과가 없습니다. 다른 검색어로 다시 시도해주세요. 예를 들어, 더 간단한 단어나 브랜드 이름으로 검색해보세요.")
                logger.info("No results returned for query='%s'", query)
            
            # 첫 배치를 표시 (results_per_page개)
            first_batch = converted_results[:self.state.results_per_page]
            self.state.search_results = first_batch
            self.state.page_offset = len(first_batch)

        except Exception as e:
            self.io_output(f"검색 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
            self.state.clear_search_results()
            logger.exception("Search failed for query='%s': %s", query, e)

    async def _select_from_search_results(self):
        """Display search results and ask user to select."""
        if not self.state.search_results:
            return

        logger.info("Displaying %d search results", len(self.state.search_results))
        
        # 첫 배치 표시
        lines = [f"\n📦 검색 결과 (페이지 {self.state.current_page}):\n"]
        for idx, result in enumerate(self.state.search_results, 1):
            lines.append(f"{idx}. {result.title}")
            lines.append(f"   가격: {result.price}")
            if result.rating:
                lines.append(f"   평점: {result.rating}")
            lines.append("")
        
        self.io_output("\n".join(lines))

        # Generate and display summary
        self.io_output("\n🤖 검색 결과 요약을 생성 중입니다...")
        summary = await asyncio.to_thread(self.llm.summarize_search_results, self.state.search_results)
        
        # Print to console with emojis
        self.console_print(f"\n{summary}\n")
        
        # Speak without emojis (for better TTS)
        if self.output_mode in ("voice", "both") and self.io:
            # Remove emojis and special markers for TTS
            # Replace newlines with period for pauses
            clean_summary = summary.replace("\n", ". ")
            # Remove characters that are NOT word chars, whitespace, comma, dot, or Korean
            clean_summary = re.sub(r'[^\w\s,.\d가-힣]', ' ', clean_summary)
            # Collapse multiple spaces
            clean_summary = re.sub(r'\s+', ' ', clean_summary).strip()
            
            logger.info("TTS Text: %s", clean_summary)
            try:
                # Speak chunk by chunk to avoid issues with long text
                chunks = [c.strip() for c in clean_summary.split('.') if c.strip()]
                for chunk in chunks:
                    self.io.speak(chunk)
            except Exception as e:
                logger.error("TTS failed: %s", e)
                self.console_print(f"⚠️  음성 출력 오류: {e}")

        # 네비게이션 옵션 표시
        print_lines = ["\n❓ 이 중에 마음에 드는 상품이 있으신가요?"]
        print_lines.append(f"🔢 상품 번호를 입력하세요 (1-{len(self.state.search_results)}), 또는:")
        
        # 페이지 내에서 더 많은 상품이 있으면 다음 상품 보기 가능
        if self.state.page_offset < len(self.state.all_search_results):
            print_lines.append("   '다음상품' → 다음 {0}개 상품 보기".format(self.state.results_per_page))
        
        # 페이지 네비게이션 옵션
        print_lines.append("   '페이지' → 다른 페이지로 이동")
        print_lines.append("   '검색' → 새로운 상품 검색")
        
        self.io_output("\n".join(print_lines))
        
        # Voice output for navigation
        if self.output_mode in ("voice", "both") and self.io:
            try:
                nav_text = f"이 중에 마음에 드는 상품이 있으신가요? 상품을 선택하시려면 1번부터 {len(self.state.search_results)}번까지 번호를 말씀해주세요"
                if self.state.page_offset < len(self.state.all_search_results):
                    nav_text += f". 다음 {self.state.results_per_page}개 상품을 더 보시려면 다음상품이라고 말씀해주세요"
                nav_text += ". 다른 페이지로 이동하시려면 페이지라고 말씀해주세요. 새로운 검색을 하시려면 검색이라고 말씀해주세요"
                self.io.speak(nav_text)
            except Exception as e:
                logger.error("Voice navigation output failed: %s", e)

    async def _select_search_result(self, selection: int):
        """Handle user's selection from search results."""
        if not (1 <= selection <= len(self.state.search_results)):
            self.io_output(f"잘못된 번호입니다. 1번부터 {len(self.state.search_results)}번 사이의 번호를 말씀해주세요.")
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
        
        lines = [f"\n📦 {start_idx + 1}번부터 {end_idx}번 상품:"]
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
            # There are more items in current page
            display_items = remaining_items
            self.state.search_results = display_items

            # Display items with 1-N numbering
            lines = [f"\n📦 페이지 {self.state.current_page}의 다음 상품들:\n"]
            for idx, result in enumerate(display_items, 1):
                lines.append(f"{idx}. {result.title}")
                lines.append(f"   가격: {result.price}")
                if result.rating:
                    lines.append(f"   평점: {result.rating}")
                lines.append("")

            self.io_output("\n".join(lines))
            self.state.page_offset = next_offset

            # Ask if user likes any of these items
            self.io_output("❓ 이 중에 마음에 드는 상품이 있으신가요?")
            # Check navigation options
            has_previous = page_start > 0
            has_next = page_end < len(self.state.all_search_results)

            print_lines = [f"🔢 상품 번호를 입력하세요 (1-{len(display_items)}), 또는:"]
            if has_previous:
                print_lines.append("   '이전' → 이전 상품 보기")
            if has_next:
                print_lines.append("   '다음상품' → 다음 상품 보기")
            print_lines.append("   '페이지' → 다른 페이지로 이동")
            print_lines.append("   '검색' → 새로운 상품 검색")
            self.io_output("\n".join(print_lines))
        else:
            # No more items in current page
            self.io_output(f"\n✅ 페이지 {self.state.current_page}의 모든 상품을 확인했습니다.")
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

            lines = [f"\n📦 페이지 {self.state.current_page}의 이전 상품들:\n"]
            for idx, result in enumerate(display_items, 1):
                lines.append(f"{idx}. {result.title}")
                lines.append(f"   가격: {result.price}")
                if result.rating:
                    lines.append(f"   평점: {result.rating}")
                lines.append("")

            self.io_output("\n".join(lines))
            # Update offset to point to end of previous batch (for consistent navigation)
            self.state.page_offset = previous_end
            # Check navigation options
            has_previous = previous_start > 0
            has_next = previous_end < len(self.state.all_search_results)

            # Ask if user likes any of these items
            self.io_output("❓ 이 중에 마음에 드는 상품이 있으신가요?")
            print_lines = [f"🔢 상품 번호를 입력하세요 (1-{len(display_items)}), 또는:"]
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
            self.io_output(f"\n⏳ 페이지 {self.state.current_page} 로드 중...")
            
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
            
            # 첫 배치 표시
            first_batch = self.state.all_search_results[:self.state.results_per_page]
            self.state.search_results = first_batch
            self.state.page_offset = len(first_batch)

            # Display first batch
            self._display_current_results()

        except Exception as e:
            logger.exception("Error loading page %d: %s", self.state.current_page, e)
            self.io_output(f"\n❌ 페이지를 불러오는 중 오류 발생: {e}")

    def _display_current_results(self):
        """Display current search results with navigation options."""
        if not self.state.search_results:
            return
        
        lines = [f"\n📦 검색 결과 (페이지 {self.state.current_page}):\n"]
        for idx, result in enumerate(self.state.search_results, 1):
            lines.append(f"{idx}. {result.title}")
            lines.append(f"   가격: {result.price}")
            if result.rating:
                lines.append(f"   평점: {result.rating}")
            lines.append("")
        self.io_output("\n".join(lines))

        # Ask if user likes any of these items
        print_lines = ["\n❓ 이 중에 마음에 드는 상품이 있으신가요?"]
        print_lines.append(f"🔢 상품 번호를 입력하세요 (1-{len(self.state.search_results)}), 또는:")
        
        if self.state.page_offset < len(self.state.all_search_results):
            print_lines.append("   '다음상품' → 다음 {0}개 상품 보기".format(self.state.results_per_page))
        
        print_lines.append("   '페이지' → 다른 페이지로 이동")
        print_lines.append("   '검색' → 새로운 상품 검색")
        
        self.io_output("\n".join(print_lines))

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
