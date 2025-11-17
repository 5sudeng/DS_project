"""LLM utilities for intent classification and query generation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI



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


class VoiceBrowserLLM:
    """LLM utilities for the voice-controlled browser agent."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 400,
    ) -> Optional[str]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            print("VoiceBrowser LLM 호출 실패:", exc)
            return None

        message = response.choices[0].message.content
        return message.strip() if message else None

    def augment_command(self, utterance: str) -> str:
        if not utterance:
            return utterance

        system_prompt = (
            "당신은 시각장애인을 돕는 브라우저 보조 AI입니다. "
            "사용자의 짧거나 모호한 명령을 더 구체적으로 다듬어줍니다."
        )
        user_prompt = f"""
사용자 명령: "{utterance}"
원본 의도를 해치지 말고 필요한 세부 정보를 한 문장으로 보완하세요.
"""

        augmented = self._chat(system_prompt, user_prompt)
        return augmented if augmented else utterance

    def parse_command(self, utterance: str, current_site: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = (
            "당신은 음성 명령을 JSON 명령으로 바꾸는 브라우저 제어 AI입니다. "
            "지원하는 action은 open_url(url), search(query), coupang_search(query), read_page(), summarize_page(), click_link(text) 입니다. "
            "사용자가 쿠팡 내부에서 검색을 원하거나 현재 페이지가 coupang.com이면 coupang_search를 사용하세요."
        )
        site_context = current_site or "알 수 없음"
        user_prompt = f"""
사용자 명령: "{utterance}"
현재 페이지: "{site_context}"
가능한 action 중 하나를 JSON 한 개로만 출력하세요. 예: {{"action":"search","query":"고양이"}}
"""

        for attempt in range(2):
            response = self._chat(system_prompt, user_prompt, temperature=0.0, max_tokens=300)
            if not response:
                continue
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                print("VoiceBrowser LLM이 JSON을 반환하지 않았습니다:", response)
                if attempt == 0:
                    print("명령 JSON 변환 재시도 중...")
                    continue
                return {"action": "none", "error": "invalid_json"}

        return {"action": "none", "error": "llm_failure"}

    def summarize_page(self, text: str) -> str:
        if not text:
            return "페이지에서 요약할 수 있는 내용이 없습니다."

        system_prompt = (
            "당신은 시각장애인을 돕는 웹 페이지 요약 도우미입니다. "
            "핵심 정보를 3-4개의 bullet로 한국어로 요약하세요."
        )
        user_prompt = f"웹 페이지 본문:\n{text}"

        summary = self._chat(system_prompt, user_prompt, temperature=0.3, max_tokens=400)
        if not summary:
            return "요약을 생성하지 못했습니다. 페이지 전체를 읽어드릴 수 있습니다."
        return summary.strip()
