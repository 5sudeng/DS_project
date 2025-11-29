"""Mixin for intent classification and handling."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

class IntentMixin:
    """Mixin for handling user intent."""

    async def _handle_user_input(self, user_input: str) -> bool:
        """Handle user input based on current state. Returns False if conversation should end."""
        logger.info("Handling user input: %s", user_input)

        # If waiting for clarification about dissatisfaction
        if self.state.waiting_for_clarification:
            logger.info("Awaiting clarification; routing response.")
            await self._handle_clarification_response(user_input)
            return True

        # Check if user is selecting from search results
        if self.state.search_results:
            if user_input.isdigit():
                logger.info("User selecting search result index=%s", user_input)
                await self._select_search_result(int(user_input))
                return True

        # Use LLM to classify intent
        intent_result = self.llm.classify_intent(
            user_input,
            self.state.conversation_history,
            self.state.current_product_name,
            artifact_summary=self.artifact_summary,
        )
        ### status
        print(f"\n[의도 파악: {intent_result['intent']} (신뢰도: {intent_result['confidence']:.2f})]")
        logger.info(
            "Intent classification result intent=%s confidence=%.2f",
            intent_result["intent"],
            intent_result["confidence"],
        )

        intent = intent_result["intent"]

        if intent == "question":
            await self._handle_question(user_input)
        elif intent == "add_to_cart":
            await self._handle_add_to_cart(intent_result)
        elif intent == "navigate_to_cart":
            await self._handle_navigate_to_cart()
        elif intent == "satisfied":
            await self._handle_satisfied()
        elif intent == "dissatisfied":
            await self._handle_dissatisfied(intent_result)
        elif intent == "exit":
            ### TODO
            print("\n👋 쇼핑을 종료합니다. 감사합니다!")
            return False
        else:
            response = intent_result.get("response_suggestion", "죄송합니다. 잘 이해하지 못했습니다. 다시 말씀해주시겠어요?")
            ### TODO
            print(f"\n🤖 {response}")
            self.state.add_message("assistant", response)

        # Check if we should suggest adding to cart (unless already adding to cart or exiting)
        if intent not in ["add_to_cart", "navigate_to_cart", "exit"] and intent_result.get("suggest_purchase"):
            await self._suggest_add_to_cart()
            
        return True

    async def _handle_question(self, question: str):
        """Handle user question about the product."""
        ### TODO
        print("\n⏳ 질문에 답변하는 중...")
        logger.info("Processing question intent: %s", question)

        answer = await self.product_agent.answer_user_question(question)
        ### TODO
        print(f"\n🤖 {answer}")

        self.state.add_message("assistant", answer)

    async def _handle_add_to_cart(self, intent_result: Dict = None):
        """Handle when user explicitly wants to add to cart."""
        ### TODO
        print("\n⏳ 장바구니에 담는 중...")
        logger.info("Processing add_to_cart intent")

        quantity = 1
        if intent_result:
            quantity = intent_result.get("quantity", 1)

        result = await self.product_agent.add_product_to_cart(quantity=quantity)
        ### TODO
        print(f"\n🤖 {result}")
        self.state.add_message("assistant", result)

        ### TODO
        print("\n💡 다른 상품을 더 찾아보시겠어요? (검색어 입력 또는 'exit'로 종료)")

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
        ### TODO
        print(f"\n🤖 {response}")
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

            ### TODO
            print(f"\n🔍 이해했습니다: {reason}")
            ### TODO
            print("새로운 상품을 찾아보겠습니다...")

            # Generate search query using LLM
            search_query = self.llm.generate_search_query(
                self.state.current_product_name,
                reason,
                keywords,
                self.state.conversation_history,
                artifact_summary=self.artifact_summary,
            )

            ### TODO
            print(f"💡 검색어: '{search_query}'")
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
            ### TODO
            print(f"\n🤖 {clarification_msg}")
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

        ### TODO
        print(f"\n🔍 알겠습니다: {reason}")
        ### TODO
        print("새로운 상품을 찾아보겠습니다...")

        search_query = self.llm.generate_search_query(
            self.state.current_product_name,
            reason,
            keywords,
            self.state.conversation_history,
            artifact_summary=self.artifact_summary,
        )

        ### TODO
        print(f"💡 검색어: '{search_query}'")
        await self._perform_search(search_query)
        await self._select_from_search_results()
        logger.info("Search triggered from clarification with query='%s'", search_query)

    async def _suggest_add_to_cart(self):
        """Suggest adding the product to cart."""
        suggestion = "\n\n💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)"
        ### TODO
        print(suggestion)
        self.state.add_message("assistant", suggestion)
