"""LLM utilities for intent classification and query generation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence

from openai import OpenAI


class PreferenceMemory:
    """Lightweight in-memory preference tracker (LangChain-friendly interface)."""

    def __init__(self):
        self._notes: List[str] = []

    def remember(self, note: str) -> None:
        if note:
            self._notes.append(note.strip())

    def summary(self, max_items: int = 5) -> str:
        if not self._notes:
            return ""
        recent = self._notes[-max_items:]
        bullets = "\n".join(f"- {item}" for item in recent if item)
        return bullets

    def has_preferences(self) -> bool:
        return bool(self._notes)

    def as_list(self) -> List[str]:
        return list(self._notes)


class ShoppingAssistantLLM:
    """LLM wrapper for shopping assistant tasks."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def classify_intent(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        current_product_info: Optional[str] = None,
        artifact_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classify user intent into categories:
        - satisfied: User wants to add to cart
        - dissatisfied: User doesn't like the product
        - question: User has a question about the product
        - clarification_needed: Need more info from user
        """

        system_prompt = """당신은 쇼핑 대화에서 사용자의 의도를 파악하는 AI입니다.

사용자의 발화를 다음 4가지 의도 중 하나로 분류하세요:
1. "satisfied": 상품이 마음에 들어서 장바구니에 담고 싶어함
2. "dissatisfied": 상품이 마음에 안 들어서 다른 상품을 찾고 싶어함
3. "question": 상품에 대한 질문
4. "other": 기타

dissatisfied인 경우, 불만족 이유를 추출하세요:
- reason: 구체적인 이유 (예: "가격이 너무 비싸다", "색상이 마음에 안든다")
- has_specific_reason: true/false (사용자가 구체적인 이유를 명시했는지)
- keywords: 새로운 검색에 사용할 키워드 리스트 (예: ["저렴한", "가성비"])

JSON 형식으로 응답하세요:
{
  "intent": "satisfied|dissatisfied|question|other",
  "confidence": 0.0-1.0,
  "reason": "이유 설명 (dissatisfied인 경우)",
  "has_specific_reason": true/false,
  "keywords": ["키워드1", "키워드2"],
  "response_suggestion": "사용자에게 할 응답 제안"
}
"""

        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])
        if current_product_info:
            context = f"현재 상품 정보: {current_product_info}\n\n{context}"
        artifact_context = self._artifact_context_snippet(artifact_summary)

        user_prompt = f"""대화 컨텍스트:
{context}

수집된 상품 데이터 요약:
{artifact_context or "정보 없음"}

현재 사용자 발화: "{user_input}"

사용자의 의도를 분류하고 JSON으로 응답하세요."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return result

    def generate_search_query(
        self,
        original_product_name: str,
        user_feedback: str,
        extracted_keywords: List[str],
        conversation_history: List[Dict[str, str]],
        artifact_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a new Coupang search query based on user feedback.
        """

        system_prompt = """당신은 사용자의 피드백을 바탕으로 쿠팡 검색어를 생성하는 AI입니다.

원본 상품 정보와 사용자의 불만족 이유를 분석하여,
사용자가 원하는 상품을 찾을 수 있는 최적의 쿠팡 검색어를 생성하세요.

검색어 생성 원칙:
1. 한국어로 작성
2. 2-5개 단어로 구성
3. 구체적이고 검색 가능한 키워드 사용
4. 상품 카테고리 + 사용자 요구사항 반영

예시:
- 원본: "나이키 운동화", 피드백: "너무 비싸" → "운동화 저렴한 가성비"
- 원본: "블랙 티셔츠", 피드백: "다른 색으로" → "티셔츠 화이트 베이지"
- 원본: "무거운 노트북", 피드백: "더 가벼운 걸로" → "노트북 경량 가벼운"

검색어만 출력하세요 (추가 설명 없이)."""

        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])
        artifact_context = self._artifact_context_snippet(artifact_summary)

        user_prompt = f"""원본 상품: {original_product_name}
사용자 피드백: {user_feedback}
추출된 키워드: {', '.join(extracted_keywords)}
참고할 상품 데이터:
{artifact_context or "정보 없음"}

대화 컨텍스트:
{context}

새로운 쿠팡 검색어를 생성하세요."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=50,
        )

        search_query = response.choices[0].message.content.strip()
        return search_query

    def ask_for_clarification(
        self,
        conversation_history: List[Dict[str, str]],
        current_product_name: str,
        artifact_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a natural clarification question when user's dissatisfaction reason is unclear.
        """

        system_prompt = """당신은 친근한 쇼핑 도우미입니다.

사용자가 상품에 만족하지 못했지만 구체적인 이유를 말하지 않았습니다.
자연스럽고 친근하게 어떤 점이 마음에 안 드는지 물어보세요.

예시:
- "어떤 점이 마음에 안 드시나요? 가격, 디자인, 기능 중에 무엇이 아쉬우신가요?"
- "다른 상품을 찾아드릴게요! 어떤 부분을 개선하면 좋을까요?"
- "좀 더 구체적으로 말씀해주시면 딱 맞는 상품을 찾아드릴 수 있어요. 가격, 색상, 사이즈 중 어떤 게 중요하신가요?"

한 문장으로 자연스럽게 질문하세요."""

        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-3:]])
        artifact_context = self._artifact_context_snippet(artifact_summary)

        user_prompt = f"""현재 상품: {current_product_name}
참고할 상품 데이터:
{artifact_context or "정보 없음"}

대화 컨텍스트:
{context}

사용자에게 불만족 이유를 물어보는 자연스러운 질문을 생성하세요."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=100,
        )

        question = response.choices[0].message.content.strip()
        return question

    def answer_product_question(
        self,
        question: str,
        snippets: List[Dict[str, str]],
        language: str = "ko",
    ) -> str:
        """
        Generate a natural language answer grounded in the provided snippets.
        """

        if not snippets:
            return "관련된 정보를 발견하지 못했습니다. 다른 내용을 확인해 볼까요?"

        formatted_snippets = self._format_snippets_for_answer(snippets)
        system_prompt = (
            "너는 쿠팡 상품 페이지를 기반으로 답변하는 쇼핑 도우미다. "
            "주어진 참고 정보만 활용해 사실에 근거한 답변을 제공하고, "
            "추측이나 미확인 정보는 언급하지 않는다."
        )
        user_prompt = f"""사용자 질문 ({language}):
{question}

참고 정보:
{formatted_snippets}

지침:
- 참고 정보에 있는 내용만 요약해서 답변하세요.
- 정보가 상충하면 가장 최근/일반적인 표현을 우선하세요.
- 확실한 근거가 없으면 정중히 모른다고 답하세요.
- 답변은 {language}로 작성하세요."""

        print(f"user_prompt for answer_product_question:\n{user_prompt}\n")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        print(f"response from answer_product_question:\n{response}\n")
        return response.choices[0].message.content.strip()

    def _artifact_context_snippet(
        self,
        artifact_summary: Optional[Dict[str, Any]],
        limit: int = 1800,
    ) -> str:
        if not artifact_summary:
            return ""
        serialized = json.dumps(artifact_summary, ensure_ascii=False, indent=2)
        if len(serialized) <= limit:
            return serialized
        return serialized[:limit] + "...(생략)"

    def _format_snippets_for_answer(
        self,
        snippets: List[Dict[str, str]],
        *,
        limit: int = 30,
        max_length: int = 1000,
    ) -> str:
        lines = []
        for idx, snippet in enumerate(snippets[:limit], 1):
            source = snippet.get("source") or "정보"
            text = self._shorten(snippet.get("text", ""), max_length)
            lines.append(f"{idx}. [{source}] {text}")
        return "\n".join(lines)

    def _shorten(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "…"

    # ─────────────────────────────────────────────────────
    # Prompt augmentation & re-query helpers
    # ─────────────────────────────────────────────────────
    def augment_user_query(
        self,
        raw_query: str,
        preference_memory: PreferenceMemory,
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Augment a vague user query using stored preferences.

        Returns:
            {
              "query": "<augmented or original>",
              "augmented": bool,
              "rationale": "<why it was changed>"
            }
        """
        pref_summary = preference_memory.summary()
        system_prompt = """당신은 사용자의 과거 선호도를 기억하는 쇼핑 비서입니다.
사용자 질문이 모호하면, 기억된 선호도를 반영해 검색어를 보강하세요.
- 선호도가 없거나, 현재 질문이 충분히 구체적이면 그대로 둡니다.
- 가격 민감, 브랜드, 색상, 배송 조건 등 과거 맥락을 반영합니다.
JSON으로만 응답하세요."""

        history_tail = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[-4:]])
        user_prompt = f"""최근 대화:
{history_tail or "없음"}

저장된 선호:
{pref_summary or "없음"}

사용자 요청: "{raw_query}"

응답 형식:
{{
  "query": "<검색어>",
  "augmented": true/false,
  "rationale": "<보강한 이유 또는 그대로 둔 이유>"
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def generate_requery_question(
        self,
        raw_query: str,
        preference_memory: PreferenceMemory,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """
        Ask a clarifying follow-up when we still lack context.
        """
        system_prompt = """당신은 쇼핑 도우미입니다.
사용자 요청이 모호하고, 저장된 선호만으로는 충분하지 않을 때 추가 질문을 한 문장으로 하세요.
가격/브랜드/색상/스타일/배송 조건 등 핵심 한두 가지만 물어보세요.
정보가 충분하면 빈 문자열로 응답하세요."""

        pref_summary = preference_memory.summary()
        history_tail = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[-3:]])
        user_prompt = f"""최근 대화:
{history_tail or "없음"}

저장된 선호:
{pref_summary or "없음"}

사용자 요청: "{raw_query}"

추가 질문(필요 없으면 빈 문자열):"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

    def summarize_products_for_user(
        self,
        products: Sequence[Any],
        preference_memory: PreferenceMemory,
        top_n: int = 3,
    ) -> str:
        """
        Summarize and rerank products on the page for the user.

        Args:
            products: iterable of objects with title/price/rating attrs or dict keys
            preference_memory: stored preferences
            top_n: how many items to highlight
        """
        pref_summary = preference_memory.summary() or "선호 정보 없음"
        product_text = self._format_products(products, limit=30)
        system_prompt = """너는 쇼핑 페이지의 여러 상품을 사용자 취향에 맞게 추천하는 AI다.
입력으로 상품 목록과 사용자 선호 요약이 주어진다.
- 가격, 평점, 특징을 고려해 간단히 재정렬한다.
- top_n개 상품을 번호 매겨 제안하고, 각 상품의 핵심 이유를 한 줄로 요약한다.
- 확신이 없으면 가볍게 제안한다."""

        user_prompt = f"""사용자 선호:
{pref_summary}

상품 목록:
{product_text}

top {top_n} 추천을 요약해줘. 각 상품당 한 줄."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()

    def _format_products(self, products: Sequence[Any], *, limit: int = 20) -> str:
        lines: List[str] = []
        for idx, prod in enumerate(list(products)[:limit], 1):
            title = getattr(prod, "title", None) or getattr(prod, "name", None) or prod.get("title") if isinstance(prod, dict) else "상품"
            price = getattr(prod, "price", None) or (prod.get("price") if isinstance(prod, dict) else None)
            rating = getattr(prod, "rating", None) or (prod.get("rating") if isinstance(prod, dict) else None)
            parts = [f"{idx}. {title}"]
            if price:
                parts.append(f"가격 {price}")
            if rating:
                parts.append(f"평점 {rating}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────
    # Voice command → action routing
    # ─────────────────────────────────────────────────────
    def map_voice_command_to_action(self, command: str) -> Dict[str, Any]:
        """
        Map a free-form voice command to a simple navigation action.

        Returns (best-effort):
        {
          "action": "open_url" | "none",
          "url": "https://...",
          "notes": "...reasoning..."
        }
        """
        # Backward compatibility: delegate to multi-action mapper
        plan = self.map_voice_command_to_actions(command)
        # Pick first open_url if exists
        for act in plan.get("actions", []):
            if act.get("action") == "open_url":
                return {"action": "open_url", "url": act.get("url"), "notes": act.get("notes", "")}
        return {"action": plan.get("actions", [{}])[0].get("action", "none") if plan.get("actions") else "none", "url": None, "notes": plan.get("notes", "")}

    def map_voice_command_to_actions(self, command: str) -> Dict[str, Any]:
        """
        Map free-form voice command to an ordered list of actions.

        Actions supported:
          - open_url: {url}
          - search_page: {query}
          - apply_sort: {sort_type}  # e.g., "낮은가격순", "높은가격순", "평점순"
          - apply_shipping: {shipping_option}  # "배송비포함" | "배송비제외"
          - summarize: {top_n:int}
          - read_results: {top_n:int}
        """
        system_prompt = """너는 사용자의 자유로운 음성 명령을 실행 가능한 액션 리스트로 변환하는 라우터다.
출력은 JSON 하나이며, actions 배열에 순서대로 기술한다.
지원 액션:
- open_url: 특정 사이트로 이동 (예: coupang.com, shopping.naver.com)
- search_page: 쿠팡 검색어 입력
- apply_sort: 쿠팡 정렬 ("낮은가격순", "높은가격순", "판매량순", "랭킹순", "최신순", "평점순")
- apply_shipping: "배송비포함" 또는 "배송비제외"
- summarize: 현재 결과를 요약/추천 (top_n 지정)
- read_results: 상위 N개 결과를 읽어줌 (top_n)

예시 변환:
- "쿠팡 들어가줘" → [{"action":"open_url","url":"https://www.coupang.com/"}]
- "후드티를 사고싶어" → [{"action":"search_page","query":"후드티"}]
- "최저가 사과를 사고싶어" → [{"action":"search_page","query":"사과"},{"action":"apply_sort","sort_type":"낮은가격순"},{"action":"read_results","top_n":3}]
- "검은색 모자를 추천해주고 별점순으로 보여줘" → [{"action":"search_page","query":"검은색 모자"},{"action":"summarize","top_n":3},{"action":"apply_sort","sort_type":"평점순"},{"action":"read_results","top_n":3}]

출력 형식:
{
  "actions": [
    {"action": "...", "...": "..."},
    ...
  ],
  "notes": "선택 근거를 짧게"
}
JSON만 응답한다."""

        user_prompt = f'사용자 명령: "{command}"\nJSON만 응답하세요.'
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"actions": [], "notes": "llm_error"}
