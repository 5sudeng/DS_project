"""LLM utilities for intent classification and query generation."""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config.settings import PROMPTS

logger = logging.getLogger(__name__)

class PreferenceMemory:
    """Structured preference + identity storage backed by memory.json."""

    CATEGORIES: List[str] = [
        "패션의류/잡화",
        "뷰티",
        "출산/유아동",
        "식품",
        "주방용품",
        "생활용품",
        "홈인테리어",
        "가전디지털",
        "스포츠/레저",
        "자동차용품",
        "도서/음반/DVD",
        "완구/취미",
        "문구/오피스",
        "반려동물용품",
        "헬스/건강식품",
    ]
    OTHER_CATEGORY = "기타"

    _CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "패션의류/잡화": ["셔츠", "바지", "신발", "가방", "모자", "코트", "자켓", "패션", "스니커"],
        "뷰티": ["화장품", "스킨", "로션", "립", "마스카라", "아이섀도", "향수", "클렌징"],
        "출산/유아동": ["기저귀", "분유", "유아", "아기", "출산", "젖병", "보행기"],
        "식품": ["라면", "과자", "커피", "식품", "음료", "간식", "냉동", "밀키트"],
        "주방용품": ["프라이팬", "냄비", "칼", "도마", "식기", "주방", "에어프라이어 용기"],
        "생활용품": ["세제", "휴지", "수건", "생활", "청소", "방향제"],
        "홈인테리어": ["침구", "커튼", "러그", "소파", "인테리어", "쿠션", "조명"],
        "가전디지털": ["노트북", "스마트폰", "가전", "디지털", "TV", "이어폰", "카메라"],
        "스포츠/레저": ["자전거", "캠핑", "등산", "운동", "요가", "트레이닝", "라켓"],
        "자동차용품": ["차량", "자동차", "타이어", "대시보드", "차량용", "블랙박스"],
        "도서/음반/DVD": ["도서", "책", "소설", "DVD", "블루레이", "음반"],
        "완구/취미": ["레고", "퍼즐", "피규어", "토이", "완구", "취미"],
        "문구/오피스": ["볼펜", "노트", "프린터", "문구", "사무", "오피스"],
        "반려동물용품": ["강아지", "고양이", "사료", "간식", "반려동물", "캣타워"],
        "헬스/건강식품": ["영양제", "비타민", "단백질", "건강", "헬스", "프로틴"],
    }

    def __init__(self, memory_path: str = "memory.json", identity_path: str = "identity.txt"):
        self.memory_path = Path(memory_path)
        self.identity_path = Path(identity_path)
        self.identity: Optional[str] = None
        self._data: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in self.CATEGORIES}
        self._data[self.OTHER_CATEGORY] = []
        self._load_files()

    # ---------------- File helpers ----------------
    def _load_files(self):
        if self.memory_path.is_file():
            try:
                loaded = json.loads(self.memory_path.read_text(encoding="utf-8"))
                categories = loaded.get("categories", {})
                for cat, events in categories.items():
                    self._data.setdefault(cat, []).extend(events)
            except Exception:
                logger.warning("Failed to load memory.json; starting fresh.")
                self._data = {cat: [] for cat in self.CATEGORIES}
                self._data[self.OTHER_CATEGORY] = []
        else:
            # Optional legacy migration from memory.txt
            legacy_txt = Path("memory.txt")
            migrated = False
            if legacy_txt.is_file():
                try:
                    lines = [ln.strip() for ln in legacy_txt.read_text(encoding="utf-8").splitlines() if ln.strip()]
                    for ln in lines:
                        self._record_event("legacy_note", {"text": ln}, self.OTHER_CATEGORY)
                    migrated = True
                except Exception:
                    logger.warning("Failed to migrate legacy memory.txt", exc_info=True)
            # Initialize empty structure
            if not migrated:
                self._data = {cat: [] for cat in self.CATEGORIES}
                self._data[self.OTHER_CATEGORY] = []

        if self.identity_path.is_file():
            try:
                self.identity = self.identity_path.read_text(encoding="utf-8").strip() or None
            except Exception:
                self.identity = None

    def _save(self) -> None:
        payload = {"categories": self._data}
        try:
            self.memory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to persist memory.json", exc_info=True)

    def clear_memory(self, clear_identity: bool = False) -> None:
        self._data = {cat: [] for cat in self.CATEGORIES}
        self._data[self.OTHER_CATEGORY] = []
        self._save()
        if clear_identity:
            self.identity = None
            try:
                if self.identity_path.exists():
                    self.identity_path.write_text("", encoding="utf-8")
            except Exception:
                pass

    def save_identity(self, identity: str) -> None:
        self.identity = identity.strip() if identity else None
        try:
            self.identity_path.write_text(self.identity or "", encoding="utf-8")
        except Exception:
            pass

    # ---------------- Category helpers ----------------
    def _normalize_category(self, category: Optional[str]) -> str:
        if not category:
            return self.OTHER_CATEGORY
        for cat in self.CATEGORIES:
            if category.strip().lower() == cat.lower():
                return cat
        return self.OTHER_CATEGORY

    def guess_category(self, text: Optional[str]) -> str:
        if not text:
            return self.OTHER_CATEGORY
        lower = text.lower()
        for cat, keywords in self._CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return cat
        return self.OTHER_CATEGORY

    # ---------------- Event helpers ----------------
    def _record_event(self, event_type: str, detail: Dict[str, Any], category: Optional[str] = None) -> None:
        category = self._normalize_category(category)
        event = {
            "type": event_type,
            "detail": detail,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        self._data.setdefault(category, []).append(event)
        self._save()

    def log_search(self, query: str, category: Optional[str] = None) -> None:
        if not query:
            return
        cat = category or self.guess_category(query)
        self._record_event("search", {"query": query}, cat)

    def log_sort(self, sort_option: str, *, query: Optional[str] = None, category: Optional[str] = None) -> None:
        if not sort_option:
            return
        cat = category or self.guess_category(query or sort_option)
        self._record_event("sort", {"sort_option": sort_option, "query": query}, cat)

    def log_related_keyword(self, keyword: str, *, base_query: Optional[str] = None, category: Optional[str] = None) -> None:
        if not keyword:
            return
        cat = category or self.guess_category(keyword or base_query)
        self._record_event("related_keyword", {"keyword": keyword, "base_query": base_query}, cat)

    def log_product_question(self, question: str, *, product_name: Optional[str] = None, category: Optional[str] = None) -> None:
        if not question:
            return
        cat = category or self.guess_category(product_name or question)
        self._record_event("product_question", {"question": question, "product": product_name}, cat)

    def log_add_to_cart(self, product_name: Optional[str], *, quantity: int = 1, category: Optional[str] = None) -> None:
        cat = category or self.guess_category(product_name)
        self._record_event("add_to_cart", {"product": product_name, "quantity": quantity}, cat)

    # ---------------- Query helpers ----------------
    def summary(self, max_items: int = 5) -> str:
        recent = self._recent_events(max_items)
        if not recent:
            return ""
        bullets = "\n".join(f"- [{item['category']}] {item['text']}" for item in recent)
        return bullets

    def has_preferences(self) -> bool:
        return any(events for events in self._data.values())

    def as_list(self) -> List[str]:
        return [entry["text"] for entry in self._recent_events(200)]

    def memory_log(self, max_lines: int = 50) -> str:
        recent = self._recent_events(max_lines)
        if not recent:
            return ""
        return "\n".join(f"[{item['category']}] {item['text']}" for item in recent)

    # ---------------- Formatting helpers ----------------
    def _recent_events(self, limit: int) -> List[Dict[str, str]]:
        flattened: List[Dict[str, Any]] = []
        for category, events in self._data.items():
            for ev in events:
                text = self._format_event(ev)
                flattened.append(
                    {
                        "category": category,
                        "text": text,
                        "ts": ev.get("ts", ""),
                    }
                )
        flattened.sort(key=lambda x: x.get("ts", ""), reverse=True)
        return flattened[:limit]

    def _format_event(self, event: Dict[str, Any]) -> str:
        etype = event.get("type")
        detail = event.get("detail", {})
        if etype == "search":
            return f"검색어: {detail.get('query')}"
        if etype == "sort":
            return f"정렬: {detail.get('sort_option')} (검색어: {detail.get('query')})"
        if etype == "related_keyword":
            base = detail.get("base_query")
            return f"연관검색어 선택: {detail.get('keyword')}" + (f" (기준: {base})" if base else "")
        if etype == "product_question":
            product = detail.get("product")
            return f"상품 질문: {detail.get('question')}" + (f" (상품: {product})" if product else "")
        if etype == "add_to_cart":
            return f"장바구니 담기: {detail.get('product')} x{detail.get('quantity', 1)}"
        if etype == "legacy_note":
            return f"이전 메모: {detail.get('text')}"
        return f"{etype}: {detail}"

class ShoppingLLMService:
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

        system_prompt = PROMPTS["classify_intent"]

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

        system_prompt = PROMPTS["generate_search_query"]

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

    def generate_product_summary(
        self,
        product_name: str,
        artifact_summary: Dict[str, Any],
    ) -> str:
        """
        Generate a concise 3-line summary of the product based on collected data.
        """
        system_prompt = PROMPTS["generate_product_summary"]

        artifact_context = self._artifact_context_snippet(artifact_summary)

        user_prompt = f"""상품명: {product_name}

수집된 데이터:
{artifact_context}

위 상품에 대한 3줄 요약을 작성해 주세요."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()

    def ask_for_clarification(
        self,
        conversation_history: List[Dict[str, str]],
        current_product_name: str,
        artifact_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a natural clarification question when user's dissatisfaction reason is unclear.
        """

        system_prompt = PROMPTS["ask_for_clarification"]

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
        basic_info: Optional[Dict[str, Any]] = None,
        language: str = "ko",
        max_images: int = 3,  # Limit images to avoid token explosion
    ) -> str:
        """
        Generate a natural language answer grounded in the provided snippets and basic info.
        Supports multimodal input with product images from snippets metadata.
        """

        if not snippets and not basic_info:
            return "관련된 정보를 발견하지 못했습니다. 다른 내용을 확인해 볼까요?"

        formatted_snippets = self._format_snippets_for_answer(snippets)
        
        basic_info_text = ""
        if basic_info:
            basic_info_text = f"기본 상품 정보:\n{json.dumps(basic_info, ensure_ascii=False, indent=2)}\n"

        system_prompt = PROMPTS["answer_product_question"]
        text_content = f"""사용자 질문 ({language}):
{question}

{basic_info_text}
참고 정보 (RAG):
{formatted_snippets}

지침:
- 기본 상품 정보와 참고 정보를 종합하여 답변하세요.
- 정보가 상충하면 기본 상품 정보를 우선하세요 (특히 가격, 상품명 등).
- 확실한 근거가 없으면 정중히 모른다고 답하세요.
- 답변은 {language}로 작성하세요."""

        # Extract images from snippets (multimodal RAG)
        image_paths = self._extract_image_paths_from_snippets(snippets)
        
        if image_paths:
            # Limit number of images
            image_paths = image_paths[:max_images]
            logger.info(f"Including {len(image_paths)} images in multimodal prompt")
            
            # Create multimodal message with images
            user_message_content = [{"type": "text", "text": text_content}]
            
            for img_path in image_paths:
                base64_image = self._encode_image_to_base64(img_path)
                if base64_image:
                    # Determine image type from extension
                    ext = Path(img_path).suffix.lower()
                    mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"
                    
                    user_message_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "low"  # Use "low" to reduce token cost
                        }
                    })
            
            print(f"user_prompt for answer_product_question (multimodal with {len(image_paths)} images):\n{text_content}\n")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message_content},
                ],
                temperature=0.2,
                max_tokens=500,  # Limit response length
            )
        else:
            # Text-only fallback
            print(f"user_prompt for answer_product_question:\n{text_content}\n")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text_content},
                ],
                temperature=0.2,
            )
        
        print(f"response from answer_product_question:\n{response}\n")
        return response.choices[0].message.content.strip()

    def rank_snippets_by_similarity(
        self,
        question: str,
        snippets: List[Dict[str, Any]],
        *,
        top_k: int = 10,
        similarity_threshold: float = 0.0,  # Filter out snippets with similarity <= 0
        embedding_model: str = "text-embedding-3-small",
    ) -> List[Dict[str, Any]]:
        """Rank snippets by cosine similarity to the question.
        
        Args:
            question: User's question
            snippets: List of snippet dictionaries
            top_k: Maximum number of snippets to return
            similarity_threshold: Minimum similarity score (cosine similarity ranges -1 to 1)
            embedding_model: OpenAI embedding model to use
            
        Returns:
            List of snippets sorted by relevance, filtered by threshold
        """
        if not snippets:
            return []

        inputs = [question] + [
            self._shorten(snippet.get("text", ""), 2000) for snippet in snippets
        ]
        response = self.client.embeddings.create(
            model=embedding_model,
            input=inputs,
        )
        data = sorted(response.data, key=lambda item: getattr(item, "index", 0))
        if len(data) < len(inputs):
            return snippets[:top_k]

        question_embedding = data[0].embedding
        snippet_embeddings = [item.embedding for item in data[1:]]

        scored: List[Dict[str, Any]] = []
        for snippet, embedding in zip(snippets, snippet_embeddings):
            score = self._cosine_similarity(question_embedding, embedding)
            enriched = dict(snippet)
            enriched["relevance_score"] = score
            scored.append(enriched)

        # Sort by relevance score (highest first)
        scored.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
        
        # Filter by similarity threshold and return top_k
        filtered = [s for s in scored if s.get("relevance_score", 0) > similarity_threshold]
        return filtered[:top_k]

    def map_command_to_actions(self, command: str) -> Dict[str, Any]:
        """
        Map free-form voice command to an ordered list of actions.
        """
        system_prompt = PROMPTS["map_actions"]
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
        except Exception as e:
            logger.error("Failed to map command to actions: %s", e)
            return {"actions": [], "notes": "llm_error"}

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
        memory_log = preference_memory.memory_log()
        identity = preference_memory.identity or ""
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

메모리 로그:
{memory_log or "없음"}

쇼핑 성향(Identity):
{identity or "미정"}

사용자 요청: "{raw_query}"

응답 형식:
{{
  "query": "<검색어>",
  "augmented": true/false,
  "rationale": "<보강한 이유 또는 그대로 둔 이유>"
}}"""

        try:
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
        except Exception as e:
            logger.error("Query augmentation failed: %s", e)
            return {"query": raw_query, "augmented": False, "rationale": "error"}

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
        memory_log = preference_memory.memory_log()
        identity = preference_memory.identity or ""
        history_tail = "\n".join([f"{m['role']}: {m['content']}" for m in conversation_history[-3:]])
        user_prompt = f"""최근 대화:
{history_tail or "없음"}

저장된 선호:
{pref_summary or "없음"}

메모리 로그:
{memory_log or "없음"}

쇼핑 성향(Identity):
{identity or "미정"}

사용자 요청: "{raw_query}"

추가 질문(필요 없으면 빈 문자열):"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Requery generation failed: %s", e)
            return ""

    def infer_shopping_identity(self, preference_memory: PreferenceMemory) -> Optional[str]:
        """Infer user's shopping identity based on accumulated memory."""
        memory_log = preference_memory.memory_log(max_lines=200)
        if not memory_log:
            return None
        system_prompt = """너는 사용자의 쇼핑 행동 로그를 보고 쇼핑 성향(MBTI 스타일)을 4축으로 분류한다.
축 정의:
- 가격: 가성비형 | 가심비형
- 속도: 로켓배송 고집형 | 배송 상관없음
- 평가: 평점/리뷰 중시 | 주관적 선택
- 충동성: 목표 구매만 | 여러 상품 즉흥 구매

출력은 한 줄로 압축:
"가격=가성비형; 속도=로켓배송; 평가=평점중시; 충동성=목표구매" 와 같이 요약.
"""
        user_prompt = f"""사용자 행동 로그:
{memory_log}

한 줄 요약으로 성향을 반환하세요."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            identity = response.choices[0].message.content.strip()
            return identity
        except Exception:
            return None

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
        """Format snippets for display in LLM prompt, including relevance scores if available."""
        lines = []
        for idx, snippet in enumerate(snippets[:limit], 1):
            source = snippet.get("source") or "정보"
            text = self._shorten(snippet.get("text", ""), max_length)
            
            # Add relevance score if available
            relevance_score = snippet.get("relevance_score")
            if relevance_score is not None:
                score_str = f"[유사도: {relevance_score:.3f}] "
                lines.append(f"{idx}. {score_str}[{source}] {text}")
            else:
                lines.append(f"{idx}. [{source}] {text}")
        return "\n".join(lines)

    def _shorten(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 1].rstrip() + "…"

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        # OpenAI 임베딩은 이미 정규화되어 있으므로 내적(Dot Product)만으로 충분합니다.
        # 단, 입력 벡터가 정규화되지 않았을 가능성이 0.1%라도 있다면 기존 코드를 유지하세요.
        return sum(x * y for x, y in zip(a, b))

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode image file to base64 string for OpenAI vision API."""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to encode image {image_path}: {e}")
            return None

    def _extract_image_paths_from_snippets(self, snippets: List[Dict[str, Any]]) -> List[str]:
        """Extract local image paths from snippets metadata."""
        image_paths = []
        for snippet in snippets:
            metadata = snippet.get("metadata", {})
            local_path = metadata.get("local_image_path")
            if local_path and Path(local_path).exists():
                image_paths.append(local_path)
        return image_paths

    def summarize_search_results(self, results: List[Any]) -> str:
        """
        Summarize the top search results.
        """
        system_prompt = PROMPTS["summarize_search_results"]
        
        # Format results for the prompt
        lines = []
        for i, r in enumerate(results[:3], 1):
            # Handle both object and dict
            title = getattr(r, "title", None) or r.get("title", "제목 없음") if isinstance(r, dict) else getattr(r, "title", "제목 없음")
            price = getattr(r, "price", None) or r.get("price", "가격 없음") if isinstance(r, dict) else getattr(r, "price", "가격 없음")
            rating = getattr(r, "rating", None) or r.get("rating", "평점 없음") if isinstance(r, dict) else getattr(r, "rating", "평점 없음")
            review_count = getattr(r, "review_count", None) or r.get("review_count", "리뷰 없음") if isinstance(r, dict) else getattr(r, "review_count", "리뷰 없음")
            
            lines.append(f"{i}. {title} | 가격: {price} | 평점: {rating} | 리뷰수: {review_count}")
            
        user_prompt = "검색 결과:\n" + "\n".join(lines)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=400,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Failed to summarize search results: %s", e)
            return "검색 결과 요약을 생성하지 못했습니다."
