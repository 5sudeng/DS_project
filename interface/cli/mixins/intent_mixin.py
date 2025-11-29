"""Mixin for intent classification and handling."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class IntentMixin:
    """Mixin for handling user intent."""

    async def _handle_user_input(self, user_input: str) -> bool:
        """Handle user input based on current state. Returns False if conversation should end."""
        logger.info("Handling user input: %s", user_input)

        # Unified planner: map natural language -> actions list
        try:
            plan = self.llm.map_command_to_actions(user_input)
        except Exception as exc:  # noqa: BLE001
            logger.error("map_command_to_actions failed: %s", exc)
            plan = {"actions": []}

        actions = plan.get("actions", []) or []
        if not actions:
            self._io_output("🤖 이해하지 못했습니다. 다른 표현으로 말씀해주세요.")
            return True

        should_continue = await self._execute_actions(actions)
        return bool(should_continue)

    async def _handle_question(self, question: str):
        """Handle user question about the product."""
        self._io_output("\n⏳ 질문에 답변하는 중...")
        logger.info("Processing question intent: %s", question)

        answer = await self.product_agent.answer_user_question(question)
        self._io_output(f"\n🤖 {answer}")

        self.state.add_message("assistant", answer)

    async def _handle_add_to_cart(self, intent_result: Dict = None):
        """Handle when user explicitly wants to add to cart."""
        self._io_output("\n⏳ 장바구니에 담는 중...")
        logger.info("Processing add_to_cart intent")

        quantity = 1
        if intent_result:
            quantity = intent_result.get("quantity", 1)

        result = await self.product_agent.add_product_to_cart(quantity=quantity)
        self._io_output(f"\n🤖 {result}")
        self.state.add_message("assistant", result)

        self._io_output("\n💡 다른 상품을 더 찾아보시겠어요? (검색어 입력 또는 'exit'로 종료)")

    async def _handle_navigate_to_cart(self):
        """Handle when user wants to navigate to cart page."""
        print("\n⏳ 장바구니 페이지로 이동 중...")
        logger.info("Processing navigate_to_cart intent")

        result = await self.product_agent.navigate_to_cart()
        print(f"\n🤖 {result}")
        self.state.add_message("assistant", result)

    async def _handle_satisfied(self):
        """Handle when user expresses satisfaction but not explicit buy command."""
        logger.info("Processing satisfied intent")
        
        response = "마음에 드신다니 다행이네요! 더 궁금한 점이 있으신가요?"
        self._io_output(f"\n🤖 {response}")
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

            self._io_output(f"\n🔍 이해했습니다: {reason}")
            self._io_output("새로운 상품을 찾아보겠습니다...")

            # Generate search query using LLM
            search_query = self.llm.generate_search_query(
                self.state.current_product_name,
                reason,
                keywords,
                self.state.conversation_history,
                artifact_summary=self.artifact_summary,
            )

            self._io_output(f"💡 검색어: '{search_query}'")
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
            self._io_output(f"\n🤖 {clarification_msg}")
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

        self._io_output(f"\n🔍 알겠습니다: {reason}")
        self._io_output("새로운 상품을 찾아보겠습니다...")

        search_query = self.llm.generate_search_query(
            self.state.current_product_name,
            reason,
            keywords,
            self.state.conversation_history,
            artifact_summary=self.artifact_summary,
        )

        self._io_output(f"💡 검색어: '{search_query}'")
        await self._perform_search(search_query)
        await self._select_from_search_results()
        logger.info("Search triggered from clarification with query='%s'", search_query)

    async def _suggest_add_to_cart(self):
        """Suggest adding the product to cart."""
        suggestion = "\n\n💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)"
        self._io_output(suggestion)
        self.state.add_message("assistant", suggestion)

    async def _execute_actions(self, actions: List[Dict[str, Any]]) -> bool:
        """Execute ordered actions produced by LLM mapping. Returns False to exit."""
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
            elif act == "select_result":
                index = action.get("index")
                if index is not None and str(index).isdigit():
                    await self._select_search_result(int(index))
            elif act == "load_product":
                target = action.get("url_or_index")
                if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
                    idx = int(target)
                    if self.state.search_results and 1 <= idx <= len(self.state.search_results):
                        await self._select_search_result(idx)
                elif isinstance(target, str):
                    await self._load_product(target)
            elif act == "question":
                query = action.get("query")
                if query:
                    await self._handle_question(query)
            elif act == "add_to_cart":
                qty = int(action.get("quantity", 1))
                await self._handle_add_to_cart({"quantity": qty})
            elif act == "navigate_to_cart":
                await self._handle_navigate_to_cart()
            elif act == "exit":
                self._io_output("\n👋 쇼핑을 종료합니다. 감사합니다!")
                return False
        return True
