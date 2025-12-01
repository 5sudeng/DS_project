"""CSS Selectors for the shopping agent."""

from typing import Dict, Sequence

SELECTORS: Dict[str, Sequence[str]] = {
    "review_section": (
        "section[data-coupang='product-review']",
        "div.sdp-review__article__list",
        "div.js_reviewArticleList",
        "section:has-text('상품평')",
    ),
    "inquiry_section": (
        "section[data-coupang='product-qna']",
        "div.sdp-review__article__list__QnA",
        "section:has-text('상품 Q&A')",
        "section:has-text('상품문의')",
    ),
    "detail_section": (
        "section[data-coupang='product-detail']",
        "div#prodDetail",
        "div.product-detail",
        "div.prod-description",
        "div.sdp-description",
    ),
    "spec_section": (
        "section:has-text('상품정보 제공고시')",
        "section:has-text('상품 정보')",
        "table.prod-delivery-policy",
        "table.prod-delivery-return-policy",
    ),
    "add_to_cart": (
        "button[data-coupang='add-to-cart']",
        "button[data-trigger='add-to-cart']",
        "button:has-text('장바구니')",
        "button:has-text('장바구니 담기')",
        "button:has-text('장바구니에 담기')",
    ),
    "cart_confirmation": (
        "div.cart-confirm",
        "div.layer-popup",
        "div.modal:has-text('장바구니')",
    ),
    "search_input": (
        "input#headerSearchKeyword",
        "input[id='headerSearchKeyword']",
        "form#headerSearchForm input",
        "input[name='q']",
        "input[type='search']",
        "input.search-input",
    ),
    "search_button": (
        "button.search-btn",
        "button[type='submit']",
        "button:has-text('검색')",
    ),
    "product_item": (
        "li.search-product",
        "li.baby-product",
        "li[id^='productItem']",
        "div.search-product-wrap",
    ),
}
