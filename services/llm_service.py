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