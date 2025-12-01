"""LLM utilities for intent classification and query generation."""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config.settings import PROMPTS

logger = logging.getLogger(__name__)

class PreferenceMemory:
    """Preference + identity storage with file-backed memory."""

    def __init__(self, memory_path: str = "memory.txt", identity_path: str = "identity.txt"):
        self._notes: List[str] = []
        self.memory_path = Path(memory_path)
        self.identity_path = Path(identity_path)
        self.identity: Optional[str] = None
        self._load_files()

    # ---------------- File helpers ----------------
    def _load_files(self):
        if self.memory_path.is_file():
            try:
                lines = self.memory_path.read_text(encoding="utf-8").splitlines()
                self._notes.extend([ln.strip() for ln in lines if ln.strip()])
            except Exception:
                pass
        if self.identity_path.is_file():
            try:
                self.identity = self.identity_path.read_text(encoding="utf-8").strip() or None
            except Exception:
                self.identity = None

    def append_event(self, text: str) -> None:
        if not text:
            return
        text = text.strip()
        self._notes.append(text)
        try:
            with self.memory_path.open("a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass

    def clear_memory(self, clear_identity: bool = False) -> None:
        self._notes.clear()
        try:
            if self.memory_path.exists():
                self.memory_path.write_text("", encoding="utf-8")
        except Exception:
            pass
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

    # ---------------- Query helpers ----------------
    def remember(self, note: str) -> None:
        self.append_event(note)

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

    def memory_log(self, max_lines: int = 50) -> str:
        if not self._notes:
            return ""
        return "\n".join(self._notes[-max_lines:])

class ShoppingLLMService:
    """LLM wrapper for shopping assistant tasks."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def map_command_to_actions(self, command: str) -> Dict[str, Any]:
        """
        Map free-form natural language to an ordered list of supported actions.
        """
        allowed_actions = """
open_url url
search_page query
apply_sort sort_type
apply_shipping shipping_option
read_results top_n
select_result index
load_product url_or_index
question query
add_to_cart quantity
navigate_to_cart
summarize top_n
exit
"""
        prompt = f"""
당신은 쇼핑 CLI의 명령 플래너입니다.
다음 액션만 사용하세요 (필요한 파라미터 포함):
{allowed_actions}

자연어 입력을 읽고 필요한 액션들을 순서대로 만드세요.
JSON 객체만 출력합니다. 형식:
{{"actions":[{{"action":"...", "param_key":"value", ...}}]}}

예시:
"쿠팡 열어줘" -> {{"actions":[{{"action":"open_url","url":"https://www.coupang.com"}}]}}
"사람들이 많이 산 좋은 헤드셋 사고싶어" -> {{"actions":[{{"action":"search_page","query":"헤드셋"}},{{"action":"apply_sort","sort_type":"판매량순"}},{{"action":"read_results","top_n":3}}]}}
"3번째 거 아이템 사고싶어" -> {{"actions":[{{"action":"select_result","index":3}},{{"action":"add_to_cart","quantity":1}}]}}
"상품 정보에 음식 칼로리가 얼마니?" -> {{"actions":[{{"action":"question","query":"음식 칼로리가 얼마니?"}}]}}
"오키 장바구니에 넣어줘" -> {{"actions":[{{"action":"add_to_cart","quantity":1}}]}}

입력: "{command}"
출력(JSON만):
"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "actions" in parsed:
                return parsed
        except Exception as exc:  # noqa: BLE001
            logger.error("map_command_to_actions failed: %s", exc)

        return {"actions": []}
    
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

        Delegates to map_command_to_actions for unified handling.
        """
        return self.map_command_to_actions(command)

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
        
    ### 위 3개 

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

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

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

    ### TODO : gen_product_summary - load product하고 분리시키기
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
