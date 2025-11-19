"""Conversation state helpers for the interactive CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from agent.coupang_search_agent import SearchResult


@dataclass
class ConversationState:
    """Maintains the state of the shopping conversation."""

    current_url: Optional[str] = None
    current_product_name: Optional[str] = None
    search_results: List["SearchResult"] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    waiting_for_clarification: bool = False
    
    # Pagination fields
    current_search_query: Optional[str] = None
    all_search_results: List["SearchResult"] = field(default_factory=list)
    current_page: int = 1
    page_offset: int = 0  # Offset within current page (for 5 items per page)
    results_per_page: int = 5
    current_sort_option: Optional[str] = None  # 현재 적용된 정렬 옵션 (예: "낮은가격순")
    current_shipping_filter: Optional[str] = None  # 현재 적용된 배송비 필터 (예: "무료배송")

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def clear_search_results(self) -> None:
        """Reset cached search results."""
        self.search_results = []
