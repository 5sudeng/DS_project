"""Mixin for intent classification and handling."""

import logging
from typing import Dict, List, Any

from services.llm_service import PreferenceMemory

logger = logging.getLogger(__name__)

class IntentMixin:
    """Mixin for handling user intent."""
    
    def __init__(self):
        # Initialize preference memory if not already done by parent/other mixins
        if not hasattr(self, 'preference_memory'):
            self.preference_memory = PreferenceMemory()
        if not hasattr(self, 'ai_memory_enabled'):
            self.ai_memory_enabled = False
            
    async def _ask_ai_memory_preference(self):
        """Ask user whether to enable AI memory (preferences/augment/re-query)."""
        if self.ai_memory_enabled:
            return
        
        self.io_output("\n🧠 AI 메모리(선호 반영/재질문) 기능을 켤까요? (예/아니오): ")
        choice = (self.io_input() or "").strip().lower()
        
        if choice in ["예", "y", "yes", "네", "ㅇㅇ"]:
            self.ai_memory_enabled = True
            self.io_output("✅ AI 메모리를 활성화했습니다. 이제 당신의 취향을 기억합니다!")
            
            # Load identity if exists
            if self.preference_memory.identity:
                self.io_output(f"📝 기억된 쇼핑 성향: {self.preference_memory.identity}")
        else:
            self.io_output("🚫 AI 메모리를 비활성화한 채로 진행합니다.")

    async def _handle_user_input(self, user_input: str) -> bool:
        """Handle user input by mapping to actions and executing them."""
        logger.info("Handling user input: %s", user_input)
        
        # 1. Save to memory if enabled
        if self.ai_memory_enabled:
            self.preference_memory.remember(f"User: {user_input}")

        # 2. Map command to actions using LLM (자연어 처리)
        result = self.llm.map_command_to_actions(user_input)
        actions = result.get("actions", [])
        notes = result.get("notes", "")
        
        if notes:
            logger.info("Action mapping notes: %s", notes)
            
        if not actions:
            # Fallback to simple conversation or error message
            response = "죄송합니다. 명령을 이해하지 못했습니다. 다시 말씀해주시겠어요?"
            self.io_output(f"\n🤖 {response}")
            self.state.add_message("assistant", response)
            return True

        # Execute actions
        await self._execute_actions(actions)
        
        # Check if any action was 'exit'
        for action in actions:
            if action.get("action") == "exit":
                # Update identity on exit if enabled
                if self.ai_memory_enabled:
                    new_identity = self.llm.infer_shopping_identity(self.preference_memory)
                    if new_identity:
                        self.preference_memory.save_identity(new_identity)
                        logger.info("Updated shopping identity: %s", new_identity)
                return False
                
        return True

    async def _execute_actions(self, actions: List[Dict[str, Any]]):
        """Execute ordered actions produced by LLM mapping."""
        for action in actions:
            act = action.get("action")
            logger.info("Executing action: %s", act)
            
            if act == "open_url":
                url = action.get("url")
                if url:
                    self.io_output(f"📡 {url}로 이동합니다...")
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    self.state.current_url = self.page.url
                    self.io_output("✅ 페이지에 접속했습니다.")
            
            elif act == "search_page":
                query = action.get("query")
                if query:
                    # Augment query if memory enabled
                    if self.ai_memory_enabled:
                        augmented_result = self.llm.augment_user_query(
                            query, 
                            self.preference_memory, 
                            self.state.conversation_history
                        )
                        augmented_query = augmented_result.get("query", query)
                        
                        if augmented_result.get("augmented") and augmented_query != query:
                            rationale = augmented_result.get("rationale", "")
                            self.io_output(f"🧠 선호를 반영해 검색어를 보강했습니다: '{augmented_query}'")
                            if rationale:
                                self.io_output(f"   (이유: {rationale})")
                            query = augmented_query
                            
                            # Check if we need more info (Re-query)
                            follow_up = self.llm.generate_requery_question(
                                query,
                                self.preference_memory,
                                self.state.conversation_history
                            )
                            
                            if follow_up:
                                self.io_output(f"\n🤔 {follow_up}")
                                answer = (self.io_input() or "").strip()
                                if answer:
                                    self.preference_memory.remember(f"Answer to '{follow_up}': {answer}")
                                    query = f"{query} {answer}"
                                    self.io_output(f"✓ '{query}'(으)로 검색합니다.")

                    await self._perform_search(query)
                    await self._select_from_search_results()
            
            elif act == "select_product":
                index = action.get("index")
                url = action.get("url")
                if index:
                    await self._select_search_result(int(index))
                elif url:
                    await self._load_product(url)
            
            elif act == "apply_sort":
                sort_type = action.get("sort_type")
                if sort_type:
                    self.io_output(f"⏳ '{sort_type}' 정렬을 적용합니다...")
                    result = await self.search_agent.apply_sort(sort_type)
                    
                    for warning in result.warnings:
                        self.console_print(f"⚠️  {warning}")
                        
                    if result.success:
                        # Update state with new results and save sort option
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
                        self.state.all_search_results = converted_results
                        self.state.search_results = converted_results[:self.state.results_per_page]
                        self.state.page_offset = len(self.state.search_results)
                        self.state.current_sort_option = sort_type  # 정렬 옵션 저장
                        self.io_output(f"✓ 정렬 완료 ({len(converted_results)}개 상품)")
                        
                        # 첫 배치 표시
                        lines = [f"\n📦 정렬된 결과 (페이지 {self.state.current_page}):\n"]
                        for idx, res in enumerate(self.state.search_results, 1):
                            lines.append(f"{idx}. {res.title}")
                            lines.append(f"   가격: {res.price}")
                            if res.rating:
                                lines.append(f"   평점: {res.rating}")
                            lines.append("")
                        self.io_output("\n".join(lines))
                    else:
                        self.io_output(f"❌ {result.error}")
            
            elif act == "apply_shipping":
                option = action.get("shipping_option")
                if option:
                    self.io_output(f"⏳ '{option}' 필터를 적용합니다...")
                    result = await self.search_agent.apply_shipping_filter(option)
                    
                    for warning in result.warnings:
                        self.console_print(f"⚠️  {warning}")
                        
                    if result.success:
                        # Update state with new results and save shipping filter
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
                        self.state.all_search_results = converted_results
                        self.state.search_results = converted_results[:self.state.results_per_page]
                        self.state.page_offset = len(self.state.search_results)
                        self.state.current_shipping_filter = option  # 배송비 필터 저장
                        self.io_output(f"✓ 필터 적용 완료 ({len(converted_results)}개 상품)")
                        
                        # 첫 배치 표시
                        lines = [f"\n📦 필터된 결과 (페이지 {self.state.current_page}):\n"]
                        for idx, res in enumerate(self.state.search_results, 1):
                            lines.append(f"{idx}. {res.title}")
                            lines.append(f"   가격: {res.price}")
                            if res.rating:
                                lines.append(f"   평점: {res.rating}")
                            lines.append("")
                        self.io_output("\n".join(lines))
                    else:
                        self.io_output(f"❌ {result.error}")
            
            elif act == "read_results":
                top_n = action.get("top_n", 3)
                await self._read_search_results(top_n)
            
            elif act == "next_items":
                count = action.get("count", 3)
                await self._show_next_results(count)
            
            elif act == "prev_items":
                count = action.get("count", 3)
                await self._show_prev_results(count)
            
            elif act == "next_page":
                if not self.state.current_search_query:
                    self.io_output("❌ 진행 중인 검색이 없습니다.")
                else:
                    # 실제 쿠팡 다음 페이지 이동
                    result = await self.search_agent.go_to_next_page()
                    if result.success:
                        self.state.current_page += 1
                        self.state.page_offset = 0
                        
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
                        
                        self.state.all_search_results = converted_results
                        first_batch = converted_results[:self.state.results_per_page]
                        self.state.search_results = first_batch
                        self.state.page_offset = len(first_batch)
                        
                        # Display results
                        self._display_current_results()
                    else:
                        self.io_output(f"❌ {result.error}")

            elif act == "prev_page":
                if not self.state.current_search_query:
                    self.io_output("❌ 진행 중인 검색이 없습니다.")
                elif self.state.current_page > 1:
                    # 실제 쿠팡 이전 페이지 이동
                    result = await self.search_agent.go_to_prev_page()
                    if result.success:
                        self.state.current_page -= 1
                        self.state.page_offset = 0
                        
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
                        
                        self.state.all_search_results = converted_results
                        first_batch = converted_results[:self.state.results_per_page]
                        self.state.search_results = first_batch
                        self.state.page_offset = len(first_batch)
                        
                        # Display results
                        self._display_current_results()
                    else:
                        self.io_output(f"❌ {result.error}")
                else:
                    self.io_output("❌ 첫 번째 페이지입니다. 이전 페이지가 없습니다.")

            elif act == "goto_page":
                page_num = action.get("page_num")
                if page_num:
                    if not self.state.current_search_query:
                        self.io_output("❌ 진행 중인 검색이 없습니다.")
                    elif int(page_num) < 1:
                        self.io_output("❌ 1 이상의 페이지 번호를 입력하세요.")
                    else:
                        self.state.current_page = int(page_num)
                        self.state.page_offset = 0
                        await self._load_current_page()
            
            elif act == "show_sort_options":
                # 정렬 옵션 안내
                sort_options = [
                    "쿠팡랭킹순",
                    "낮은가격순",
                    "높은가격순",
                    "판매량순",
                    "최신순",
                ]
                message = "\n 사용 가능한 정렬 옵션:\n\n" + "\n".join([f"  • {opt}" for opt in sort_options])
                self.io_output(message)
            
            elif act == "show_related_keywords":
                await self._handle_related_keywords()
            
            elif act == "select_related_keyword":
                keyword = action.get("keyword")
                if keyword:
                    await self._select_related_keyword(keyword)
            
            elif act == "question":
                query = action.get("query")
                if query:
                    await self._handle_question(query)
            
            elif act == "add_to_cart":
                quantity = action.get("quantity", 1)
                await self._handle_add_to_cart({"quantity": quantity})
            
            elif act == "navigate_to_cart":
                await self._handle_navigate_to_cart()
            
            elif act == "summarize":
                top_n = action.get("top_n", 3)
                await self._summarize_search_results(top_n)
            
            elif act == "exit":
                self.io_output("\n👋 쇼핑을 종료합니다. 감사합니다!")

    async def _summarize_search_results(self, top_n: int):
        """Summarize the search results using LLM."""
        if not self.state.search_results:
            self.io_output("❌ 요약할 검색 결과가 없습니다.")
            return

        self.io_output(f"\n🧠 상위 {top_n}개 상품을 분석하고 있습니다...")
        
        # Prepare context for LLM
        items = self.state.search_results[:top_n]
        items_text = "\n".join([
            f"{i+1}. {item.title} (가격: {item.price}, 평점: {item.rating or '없음'})"
            for i, item in enumerate(items)
        ])
        
        try:
            # Display items as summary
            self.io_output(f"\n[검색 결과 요약]\n{items_text}")
            self.io_output("\n(상세한 AI 요약 기능은 준비 중입니다)")
            
        except Exception as e:
            logger.error("Failed to summarize results: %s", e)
            self.io_output("⚠️ 요약 정보를 생성하지 못했습니다.")

    async def _handle_question(self, question: str):
        """Handle user question about the product."""
        self.io_output("\n⏳ 질문에 답변하는 중...")
        logger.info("Processing question intent: %s", question)

        answer = await self.product_agent.answer_user_question(question)
        self.io_output(f"\n🤖 {answer}")
        self.state.add_message("assistant", answer)

    async def _handle_add_to_cart(self, intent_result: Dict = None):
        """Handle when user explicitly wants to add to cart."""
        self.io_output("\n⏳ 장바구니에 담는 중...")
        logger.info("Processing add_to_cart intent")

        quantity = 1
        if intent_result:
            quantity = intent_result.get("quantity", 1)

        result = await self.product_agent.add_product_to_cart(quantity=quantity)
        
        # Handle warnings
        for warning in result.warnings:
            self.console_print(f"⚠️  {warning}")
        
        if result.success:
            self.io_output(f"\n🤖 {result.message}")
            self.state.add_message("assistant", result.message)
            self.io_output("\n💡 다른 상품을 더 찾아보시겠어요? (검색어 입력 또는 'exit'로 종료)")
        else:
            self.io_output(f"\n❌ {result.error}")
            self.state.add_message("assistant", result.error)

    async def _handle_navigate_to_cart(self):
        """Handle when user wants to navigate to cart page."""
        self.console_print("\n⏳ 장바구니 페이지로 이동 중...")
        logger.info("Processing navigate_to_cart intent")

        result = await self.product_agent.navigate_to_cart()
        
        # Handle warnings
        for warning in result.warnings:
            self.console_print(f"⚠️  {warning}")
        
        if result.success:
            self.io_output(f"\n🤖 {result.message}")
            self.state.add_message("assistant", result.message)
        else:
            self.io_output(f"\n❌ {result.error}")
            self.state.add_message("assistant", result.error)

    async def _handle_satisfied(self):
        """Handle when user expresses satisfaction but not explicit buy command."""
        logger.info("Processing satisfied intent")
        
        response = "마음에 드신다니 다행이네요! 더 궁금한 점이 있으신가요?"
        self.io_output(f"\n🤖 {response}")
        self.state.add_message("assistant", response)

    async def _handle_dissatisfied(self, intent_result: Dict):
        """Handle when user is dissatisfied with the product."""
        logger.info(
            "Processing dissatisfied intent has_specific_reason=%s",
            intent_result.get("has_specific_reason"),
        )

        if intent_result.get("has_specific_reason"):
            # User provided specific reason
            reason = intent_result["reason"]
            keywords = intent_result.get("keywords", [])

            self.io_output(f"\n🔍 이해했습니다: {reason}")
            self.io_output("새로운 상품을 찾아보겠습니다...")

            # Generate search query using LLM
            search_query = self.llm.generate_search_query(
                self.state.current_product_name,
                reason,
                keywords,
                self.state.conversation_history,
                artifact_summary=self.artifact_summary,
            )

            self.io_output(f"💡 검색어: '{search_query}'")
            await self._perform_search(search_query)
            await self._select_from_search_results()
            logger.info("Search triggered with query='%s'", search_query)

        else:
            # Need clarification from user
            clarification_msg = self.llm.ask_for_clarification(
                self.state.conversation_history,
                self.state.current_product_name,
                artifact_summary=self.artifact_summary,
            )
            self.io_output(f"\n🤖 {clarification_msg}")
            self.state.add_message("assistant", clarification_msg)
            self.state.waiting_for_clarification = True
            logger.info("Asked user for clarification regarding dissatisfaction.")

    async def _handle_clarification_response(self, user_input: str):
        """Handle user's response to clarification question."""
        self.state.waiting_for_clarification = False
        logger.info("Received clarification response: %s", user_input)

        # Re-classify with the new information
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
            artifact_summary=self.artifact_summary,
        )

        reason = intent_result.get("reason", user_input)
        keywords = intent_result.get("keywords", [])

        self.io_output(f"\n🔍 알겠습니다: {reason}")
        self.io_output("새로운 상품을 찾아보겠습니다...")

        search_query = self.llm.generate_search_query(
            self.state.current_product_name,
            reason,
            keywords,
            self.state.conversation_history,
            artifact_summary=self.artifact_summary,
        )

        self.io_output(f"💡 검색어: '{search_query}'")
        await self._perform_search(search_query)
        await self._select_from_search_results()
        logger.info("Search triggered from clarification with query='%s'", search_query)

    async def _suggest_add_to_cart(self):
        """Suggest adding the product to cart."""
        suggestion = "\n\n💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)"
        self.io_output(suggestion)
        self.state.add_message("assistant", suggestion)