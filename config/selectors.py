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
        "input[name='q']",
        "input[type='search']",
        "input.search-input",
        "input[placeholder*='검색']",
        "input[placeholder*='Search']",
        "input.search__input",
        ".search-input-wrapper input",
        "header input[type='text']",
    ),
    "search_button": (
        "button.search-btn",
        "button[type='submit']",
        "button:has-text('검색')",
    ),
    "product_item": (
        # 실제 검색 결과만 선택 (광고, 추천, 특가 제외)
        "ul#product-list > li:not(:has-text('AD')):not(:has-text('광고')):not(:has-text('특가진행중'))",
        "ul#product-list > li",
        "ul.search-product-list > li.search-product:not(:has-text('AD')):not(:has-text('광고')):not(:has-text('특가진행중'))",
        "ul.search-product-list > li.search-product",  # 메인 검색 결과 리스트
        "div.search-product-wrap-list > li.search-product",
        "li.search-product:not([class*='ad']):not([class*='recommend']):not([class*='promotion'])",
        "li[id^='productItem']",
    ),
    "sort_buttons": {
        "랭킹순": [
            "button[data-testid='sorter-tab-ranking']",
            "a:has-text('랭킹순')",
            "button:has-text('랭킹순')",
            "li:has-text('랭킹순')",
        ],
        "낮은가격순": [
            "button[data-testid='sorter-tab-priceAsc']",
            "a:has-text('낮은가격순')",
            "button:has-text('낮은가격순')",
            "li:has-text('낮은가격순')",
        ],
        "높은가격순": [
            "button[data-testid='sorter-tab-priceDesc']",
            "a:has-text('높은가격순')",
            "button:has-text('높은가격순')",
            "li:has-text('높은가격순')",
        ],
        "판매량순": [
            "button[data-testid='sorter-tab-saleCount']",
            "a:has-text('판매량순')",
            "button:has-text('판매량순')",
            "li:has-text('판매량순')",
        ],
        "최신순": [
            "button[data-testid='sorter-tab-latest']",
            "a:has-text('최신순')",
            "button:has-text('최신순')",
            "li:has-text('최신순')",
        ],
    },
    "shipping_filter": (
        # 배송비 포함/제외 토글 버튼 (최신 쿠팡 구조)
        "button[data-testid='delivery-fee-toggle']",
        "div.srp_deliveryFeeToggle__6HXTR button",
        "div[class*='deliveryFeeToggle'] button",
        "button:has-text('배송비')",
        "label:has-text('배송비') button",
    ),
    "related_keywords": (
        "div.srp_relatedKeywords__DJiuK a",
        "div[class*='related'] a",
        "div[class*='srp_related'] a",
    )
}
