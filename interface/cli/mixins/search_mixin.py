"""Mixin for search functionality."""

import logging

logger = logging.getLogger(__name__)

class SearchMixin:
    """Mixin for handling product search."""

    async def _start_with_search(self):
        """Start with a product search."""
        self.io_output("🔍 검색어를 입력하세요: ")
        query = (self.io_input() or "").strip()
        if not query:
            ### TODO
            self.io_output("❌ 검색어를 입력해주세요.")
            await self._get_initial_product()
            return

        await self._perform_search(query)
        await self._select_from_search_results()

    async def _perform_search(self, query: str):
        """Perform a product search."""
        logger.info("Performing search query='%s'", query)
        ### status
        self.console_print(f"\n🔍 검색 중: '{query}'")
        
        try:
            result = await self.search_agent.search(query, max_results=5)
            
            # Handle warnings
            for warning in result.warnings:
                ### status
                self.console_print(f"⚠️  {warning}")
            
            if not result.success:
                ### TODO
                self.io_output(f"\n❌ {result.error}")
                self.state.search_results = []
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
            
            self.state.search_results = converted_results
            ### status
            self.console_print(f"✓ {len(converted_results)}개 상품 발견")

            if not converted_results:
                ### TODO
                self.io_output("\n😔 검색 결과가 없습니다. 다른 검색어로 시도해주세요.")
                logger.info("No results returned for query='%s'", query)

        except Exception as e:
            ### TODO
            self.io_output(f"\n❌ 검색 중 예상치 못한 오류 발생: {e}")
            self.state.search_results = []
            logger.exception("Search failed for query='%s': %s", query, e)

    async def _select_from_search_results(self):
        """Display search results and ask user to select."""
        if not self.state.search_results:
            return

        logger.info("Displaying %d search results", len(self.state.search_results))
        display_text = self.search_agent.format_results_for_display(self.state.search_results)
        ### TODO
        self.io_output(display_text)
        ### TODO
        self.io_output("🔢 원하는 상품의 번호를 입력하세요 (1-5):")

    async def _select_search_result(self, selection: int):
        """Handle user's selection from search results."""
        if not (1 <= selection <= len(self.state.search_results)):
            ### TODO
            self.io_output(f"❌ 1부터 {len(self.state.search_results)} 사이의 번호를 입력해주세요.")
            return

        logger.info("User selected result index=%d", selection)
        selected = self.state.search_results[selection - 1]
        ### TODO
        self.io_output(f"\n✓ 선택: {selected.title}")

        # Clear search results and load new product
        self.state.clear_search_results()
        loaded = await self._load_product(selected.url)
        if not loaded:
            ### TODO
            self.io_output("⚠️  선택한 상품을 불러오지 못했습니다. 다른 상품을 선택해 주세요.")
