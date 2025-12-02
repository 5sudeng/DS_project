"""Conversation state helpers for the interactive CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from services.search_service import SearchResult


@dataclass
class ConversationState:
    """Maintains the state of the shopping conversation."""

    current_url: Optional[str] = None
    current_product_name: Optional[str] = None
    search_results: List["SearchResult"] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    waiting_for_clarification: bool = False
    results_per_page: int = 3

    # 페이지 내 상품 탐색 관련
    all_search_results: List["SearchResult"] = field(default_factory=list)  # 현재 페이지의 모든 상품
    page_offset: int = 0  # 현재 표시 중인 상품의 끝 인덱스
    
    # 페이지 네비게이션 관련
    current_page: int = 1
    current_search_query: Optional[str] = None
    
    # 정렬/필터 상태 유지
    current_sort_option: Optional[str] = None  # 예: "랭킹순", "낮은가격순"
    current_shipping_filter: Optional[str] = None  # 예: "배송비포함", "배송비제외"

    # 사용자 안내 문구 제어
    guidance_shown_for_page: bool = False  # 현재 페이지에서 일반 안내를 이미 표시했는지 여부
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def clear_search_results(self) -> None:
        """Reset cached search results."""
        self.search_results = []
        self.all_search_results = []
        self.page_offset = 0
