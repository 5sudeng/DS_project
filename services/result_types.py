"""Result types for service layer to avoid UI coupling."""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class NavigationResult:
    """Result of navigation operations."""
    success: bool
    message: str
    url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CartOperationResult:
    """Result of cart operations (add to cart, navigate to cart)."""
    success: bool
    message: str
    quantity_added: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SearchResult:
    """Single search result item."""
    index: int
    title: str
    price: str
    url: str
    rating: Optional[str] = None


@dataclass
class SearchOperationResult:
    """Result of search operations."""
    success: bool
    results: List[SearchResult] = field(default_factory=list)
    query: Optional[str] = None
    total_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ProductLoadResult:
    """Result of product page loading operations."""
    success: bool
    product_name: Optional[str] = None
    url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
