"""Playwright-based Coupang shopping assistant agent.

This module implements scenario logic for interacting with a Coupang product
page after navigation has already happened.  The agent supports the following
capabilities:

2. Add the product to the shopping cart when the user confirms interest.
3. Ask the user for feedback and trigger a refreshed search flow if the user is
   not satisfied.

The implementation focuses on the conversation fragment described in the
product detail page scenario:

User:  "발볼 넓은 사람도 신을 수 있대?"
System: "구매 후기에서 ‘발볼이 넓어도 편하게 맞는다’는 평가가 있었습니다. 대부분
         정사이즈를 추천하고 있습니다."
User A: "좋아, 장바구니 넣어줘"  -> add to cart.
User B: "맘에 안들어" -> ask for more details and refresh search terms.

The module exposes a ``CoupangProductAgent`` class which operates on a
``playwright.async_api.Page`` instance.  The class only assumes that the page is
already on a valid product detail view and encapsulates all DOM interaction,
including multiple fallbacks to support layout variations on Coupang.

Example usage (interactive demo):

.. code-block:: python

    import asyncio
    from agent.coupang_playwright_agent import run_demo

    asyncio.run(run_demo(
        url="https://www.coupang.com/vp/products/XXXXX",
        user_follow_up="좋아, 장바구니 넣어줘"
    ))

The demo function can be executed with scenario A or B by toggling the
``user_follow_up`` argument.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence
import os

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from services.llm_service import ShoppingLLMService
from config.selectors import SELECTORS


@dataclass

class BrowserService:
    """Playwright-driven helper that supports the product-page dialog."""

    DEFAULT_CHUNK_DATA_PATH = Path("data/exports_normalized/chunked_data_output.json")

    REVIEW_SECTION_SELECTORS: Sequence[str] = SELECTORS["review_section"]
    INQUIRY_SECTION_SELECTORS: Sequence[str] = SELECTORS["inquiry_section"]
    DETAIL_SECTION_SELECTORS: Sequence[str] = SELECTORS["detail_section"]
    SPEC_SECTION_SELECTORS: Sequence[str] = SELECTORS["spec_section"]
    ADD_TO_CART_SELECTORS: Sequence[str] = SELECTORS["add_to_cart"]
    CART_CONFIRMATION_SELECTORS: Sequence[str] = SELECTORS["cart_confirmation"]

    def __init__(
        self,
        page: Page,
        *,
        search_timeout: float = 1.5,
        chunk_data_path: Optional[str] = None,
        test_mode: Optional[bool] = None,
        llm: Optional[ShoppingLLMService] = None,
    ) -> None:
        self.page = page
        self.search_timeout = search_timeout
        self._llm = llm
        self._llm_initialized = llm is not None
        self.chunk_data_path = (
            Path(chunk_data_path).expanduser() if chunk_data_path else self.DEFAULT_CHUNK_DATA_PATH
        )
        self._chunk_dataset: Optional[List[dict]] = None
        env_test_flag = os.getenv("TEST_FLAG")
        if test_mode is not None:
            self.test_mode = test_mode
        elif env_test_flag is None:
            self.test_mode = False
        else:
            self.test_mode = env_test_flag.strip().lower() not in {"", "0", "false", "no"}

    async def answer_user_question(self, utterance: str) -> str:
        """Return a synthesized answer based on reviews, inquiries, and detail sections."""

        snippets = self._collect_chunked_dataset_snippets(limit=100)

        if not snippets:
            section_tasks = [
                self._collect_section_snippets(
                    self.REVIEW_SECTION_SELECTORS, label="구매 후기", max_snippets=4
                ),
                self._collect_section_snippets(
                    self.INQUIRY_SECTION_SELECTORS, label="상품 문의", max_snippets=3
                ),
                self._collect_section_snippets(
                    self.DETAIL_SECTION_SELECTORS, label="상세 설명", max_snippets=2
                ),
                self._collect_section_snippets(
                    self.SPEC_SECTION_SELECTORS, label="상품 정보", max_snippets=2
                ),
            ]

            results = await asyncio.gather(*section_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    continue
                snippets.extend(result)

        # Deduplicate snippets based on text content
        unique_snippets = []
        seen_texts = set()
        for s in snippets:
            text = s.get("text", "").strip()
            if text and text not in seen_texts:
                unique_snippets.append(s)
                seen_texts.add(text)
        snippets = unique_snippets
        if not snippets:
            return "관련 정보를 찾지 못했습니다. 다른 내용을 도와드릴까요?"

        llm = self._ensure_llm()
        if not llm:
            return "답변 생성 모델을 초기화하지 못했습니다. 잠시 후 다시 시도해 주시겠어요?"

        relevant_snippets = self._select_relevant_snippets_for_question(
            utterance,
            snippets,
            llm,
            top_k=10,
        )
        print(f"✓ 질문과 관련 있는 {len(relevant_snippets)}개 근거만 활용합니다.")

        # Extract basic info from the page
        basic_info = await self._extract_basic_info()

        try:
            return llm.answer_product_question(
                utterance,
                relevant_snippets,
                basic_info=basic_info,
                language="ko",
            )
        except Exception as exc:  # noqa: BLE001
            return f"답변 생성 중 문제가 발생했습니다: {exc}"


    async def add_product_to_cart(self, quantity: int = 1) -> str:
        """Click the add-to-cart button and confirm the action."""

        # Handle quantity if greater than 1
        if quantity > 1:
            try:
                # Try to find quantity input
                # Common selectors for quantity input
                qty_selectors = [
                    "input[type='number'][class*='quantity']",
                    "input[class*='quantity']",
                    ".prod-quantity__input",
                    "input[name='quantity']"
                ]
                
                qty_input = None
                for sel in qty_selectors:
                    loc = self.page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        qty_input = loc
                        break
                
                if qty_input:
                    await qty_input.fill(str(quantity))
                    # Trigger change event if needed
                    await qty_input.dispatch_event("change")
                    print(f"✓ 수량을 {quantity}개로 변경했습니다.")
                else:
                    print(f"⚠️  수량 입력창을 찾지 못해 기본 수량(1개)으로 진행합니다.")
            except Exception as e:
                print(f"⚠️  수량 변경 중 오류 발생: {e}")

        for selector in self.ADD_TO_CART_SELECTORS:
            try:
                button = self.page.locator(selector)
                if await button.count() == 0:
                    continue
                await button.first.click(timeout=self.search_timeout * 1000)
                await self._wait_for_cart_confirmation()
                return f"{quantity}개 상품을 장바구니에 담았습니다. 다른 필요한 게 있으신가요?"
            except PlaywrightTimeoutError:
                continue
        return "장바구니 버튼을 찾을 수 없었습니다. 직접 눌러 주시겠어요?"

    async def ask_for_preference_feedback(self) -> str:
        """Prompt the user for specific dissatisfaction feedback."""

        # In a full implementation this could trigger a new search with refined
        # keywords.  The Playwright layer simply prepares the prompt message.
        return "어떤 점이 마음에 안드시나요? 마음에 드는 물건을 추천해드릴게요."


    async def _collect_locator_text(self, locator: Locator) -> List[str]:
        """Extract text from the given locator, avoiding duplicates."""

        texts: List[str] = []
        element_handles = await locator.element_handles()
        for handle in element_handles:
            try:
                text = await handle.inner_text()
            except PlaywrightTimeoutError:
                continue
            if text:
                texts.append(text)
        return texts

    async def _wait_for_cart_confirmation(self) -> None:
        for selector in self.CART_CONFIRMATION_SELECTORS:
            try:
                await self.page.wait_for_selector(
                    selector,
                    timeout=int(self.search_timeout * 1000),
                    state="visible",
                )
                return
            except PlaywrightTimeoutError:
                continue


    def _normalize_text(self, text: str) -> str:
        normalized = " ".join(text.split())
        return normalized.strip()

    def _collect_chunked_dataset_snippets(
        self,
        *,
        limit: int = 100,
        per_source_limit: int = 100,
    ) -> List[dict]:
        dataset = self._load_chunk_dataset()
        print(f"✓ 청크 데이터셋에서 {len(dataset)}개 청크 로드됨")
        print(f"✓ 최대 {limit}개 청크에서 대표 텍스트 추출 시도")
        print(f"✓ 출처별 최대 {per_source_limit}개 청크 허용됨")
        if not dataset:
            return []

        snippets: List[dict] = []
        per_source_counts: dict[str, int] = {}

        for chunk in dataset:
            if len(snippets) >= limit:
                break
            text = self._normalize_text(chunk.get("text_content") or "")
            if not text:
                continue
            source_type = (chunk.get("source_type") or "data").lower()
            if per_source_counts.get(source_type, 0) >= per_source_limit:
                continue

            snippets.append(
                {
                    "source": self._format_chunk_source(chunk),
                    "text": text,
                    "chunk_id": chunk.get("chunk_id"),
                    "metadata": chunk.get("metadata"),
                }
            )
            per_source_counts[source_type] = per_source_counts.get(source_type, 0) + 1

        return snippets

    def _select_relevant_snippets_for_question(
        self,
        question: str,
        snippets: List[dict],
        llm: ShoppingLLMService,
        *,
        top_k: int = 10,
    ) -> List[dict]:
        if not snippets:
            return []
        try:
            ranked = llm.rank_snippets_by_similarity(
                question,
                snippets,
                top_k=top_k,
            )
            if ranked:
                return ranked
        except Exception:
            pass
        return snippets[:top_k]

    def _load_chunk_dataset(self) -> List[dict]:
        if self._chunk_dataset is not None:
            return self._chunk_dataset

        data = self._read_chunk_file(self.chunk_data_path)

        if data is None and self.test_mode:
            fallback_path = self._find_latest_chunk_file()
            if fallback_path and fallback_path != self.chunk_data_path:
                data = self._read_chunk_file(fallback_path)
                if data is not None:
                    self.chunk_data_path = fallback_path

        self._chunk_dataset = data or []
        return self._chunk_dataset

    def _format_chunk_source(self, chunk: dict) -> str:
        source_file = chunk.get("source_file") or "chunk"
        source_type = chunk.get("source_type") or "data"
        origin = (chunk.get("metadata") or {}).get("origin_field") or ""
        if origin:
            return f"{source_type}:{origin} ({source_file})"
        return f"{source_type} ({source_file})"

    def _read_chunk_file(self, path: Optional[Path]) -> Optional[List[dict]]:
        if not path or not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
        except Exception:  # noqa: BLE001
            return None

    def _find_latest_chunk_file(self) -> Optional[Path]:
        base = Path("outputs/scenario_runs")
        if not base.exists():
            return None
        candidates = list(base.glob("*/chunked_data_output.json"))
        if not candidates:
            return None
        try:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:  # noqa: BLE001
            return None
        return candidates[0]

    async def _collect_section_snippets(
        self,
        selectors: Sequence[str],
        *,
        label: str,
        max_snippets: int,
    ) -> List[dict]:
        """Collect representative text snippets from the given selectors."""

        snippets: List[dict] = []
        seen: set[str] = set()

        for selector in selectors:
            if len(snippets) >= max_snippets:
                break

            locator = self.page.locator(selector)
            try:
                if await locator.count() == 0:
                    continue
                texts = await self._collect_locator_text(locator)
            except PlaywrightTimeoutError:
                continue

            for text in texts:
                normalized = self._normalize_text(text)
                if not normalized or normalized in seen:
                    continue
                snippets.append({"source": label, "text": normalized})
                seen.add(normalized)
                if len(snippets) >= max_snippets:
                    break

        return snippets

    def _ensure_llm(self) -> Optional[ShoppingLLMService]:
        if not self._llm_initialized:
            # Fallback for legacy usage or if not injected
            self._llm_initialized = True
            try:
                self._llm = ShoppingLLMService()
            except Exception:  # noqa: BLE001
                self._llm = None
        return self._llm

    async def _extract_basic_info(self) -> Dict[str, Any]:
        """Extract basic product information from the page."""
        import re
        info = {}
        
        # PRIORITY 1: JSON-LD Schema (most reliable)
        try:
            page_content = await self.page.content()
            # Look for JSON-LD script tag
            json_ld_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page_content, re.DOTALL)
            if json_ld_match:
                try:
                    json_ld_text = json_ld_match.group(1).strip()
                    json_ld_data = json.loads(json_ld_text)
                    
                    # Extract from Product schema
                    if json_ld_data.get("@type") == "Product":
                        # Product Name
                        if "name" in json_ld_data:
                            info["product_name"] = json_ld_data["name"]
                        # Price
                        if "offers" in json_ld_data and "price" in json_ld_data["offers"]:
                            price_val = json_ld_data["offers"]["price"]
                            info["price"] = f"{int(price_val):,}원" if price_val else None
                        
                        # Original Price (from priceSpecification)
                        if "offers" in json_ld_data and "priceSpecification" in json_ld_data["offers"]:
                            orig_price = json_ld_data["offers"]["priceSpecification"].get("price")
                            if orig_price:
                                info["original_price"] = f"{int(orig_price):,}원"
                        
                        # Brand
                        if "brand" in json_ld_data and "name" in json_ld_data["brand"]:
                            info["brand"] = json_ld_data["brand"]["name"]
                        
                        # Rating
                        if "aggregateRating" in json_ld_data:
                            rating_data = json_ld_data["aggregateRating"]
                            if "ratingValue" in rating_data:
                                info["rating"] = str(rating_data["ratingValue"])
                            if "ratingCount" in rating_data:
                                info["review_count"] = f"({rating_data['ratingCount']:,})"
                except Exception as e:
                    pass  # Continue to DOM selectors if JSON-LD parsing fails
        except Exception:
            pass
        
        # PRIORITY 2: DOM Selectors (fallback if JSON-LD missing info)
        
        # Product Title (if not from JSON-LD)
        if "product_name" not in info:
            try:
                title_el = self.page.locator("h2.prod-buy-header__title").first
                if await title_el.count() > 0:
                    info["product_name"] = await title_el.inner_text()
            except Exception:
                pass

        # Price (가격) - Only if not from JSON-LD
        if "price" not in info:
            try:
                # Wait for price container to be visible
                try:
                    await self.page.wait_for_selector("div.price-container, span.final-price-amount, span.total-price", timeout=3000)
                except Exception:
                    pass  # Continue even if timeout
                
                # Try multiple selectors for price
                price_selectors = [
                    "span.final-price-amount",  # New design
                    "span.sales-price-amount",  # Alternative
                    "span.total-price > strong",  # Old design
                    "div.final-price span",  # Fallback
                ]
                
                for selector in price_selectors:
                    try:
                        price_el = self.page.locator(selector).first
                        if await price_el.count() > 0:
                            price_text = await price_el.inner_text()
                            if price_text and price_text.strip():
                                info["price"] = price_text.strip()
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Original Price (정가) - Only if not from JSON-LD
        if "original_price" not in info:
            try:
                orig_price_el = self.page.locator("span.original-price-amount").first
                if await orig_price_el.count() > 0:
                    info["original_price"] = await orig_price_el.inner_text()
            except Exception:
                pass

        # Rating - Only if not from JSON-LD
        if "rating" not in info:
            try:
                rating_el = self.page.locator("span.rating-star-num").first
                if await rating_el.count() > 0:
                    info["rating"] = await rating_el.inner_text()
            except Exception:
                pass
            
        # Review Count - Only if not from JSON-LD
        if "review_count" not in info:
            try:
                review_count_el = self.page.locator("span.count").first
                if await review_count_el.count() > 0:
                    info["review_count"] = await review_count_el.inner_text()
            except Exception:
                pass

        # Brand (브랜드) - Only if not from JSON-LD
        if "brand" not in info:
            try:
                brand_el = self.page.locator("div.brand-info, a.prod-brand-name").first
                if await brand_el.count() > 0:
                    info["brand"] = await brand_el.inner_text()
            except Exception:
                pass

        # Origin (원산지)
        try:
            origin_el = self.page.locator("div.country-of-origin").first
            if await origin_el.count() > 0:
                origin_text = await origin_el.inner_text()
                # Remove "원산지: " prefix if present
                info["origin"] = origin_text.replace("원산지:", "").strip()
        except Exception:
            pass

        # Delivery Info (배송 정보)
        try:
            delivery_el = self.page.locator("div.delivery-container, div.prod-shipping-fee-message").first
            if await delivery_el.count() > 0:
                info["delivery_info"] = await delivery_el.inner_text()
        except Exception:
            pass

        # Rocket Delivery Badge (로켓배송)
        try:
            rocket_el = self.page.locator("[class*='rocket'], [class*='Rocket']").first
            if await rocket_el.count() > 0:
                info["is_rocket_delivery"] = True
        except Exception:
            pass

        # Discount Rate (할인율)
        try:
            # Calculate from original price and current price if both exist
            if "original_price" in info and "price" in info:
                try:
                    # Extract numeric values
                    orig = re.sub(r'[^\d]', '', info["original_price"])
                    curr = re.sub(r'[^\d]', '', info["price"])
                    if orig and curr:
                        orig_val = int(orig)
                        curr_val = int(curr)
                        if orig_val > curr_val:
                            discount_rate = round(((orig_val - curr_val) / orig_val) * 100)
                            info["discount_rate"] = f"{discount_rate}%"
                except Exception:
                    pass
        except Exception:
            pass

        # Stock Status (재고 상태)
        try:
            # Check for out of stock message
            stock_el = self.page.locator("[class*='sold-out'], [class*='out-of-stock']").first
            if await stock_el.count() > 0:
                info["stock_status"] = "품절"
            else:
                info["stock_status"] = "판매중"
        except Exception:
            pass

        # Seller Info (판매자)
        try:
            seller_el = self.page.locator("a.prod-sale-vendor-name, div.prod-sold-by").first
            if await seller_el.count() > 0:
                info["seller"] = await seller_el.inner_text()
        except Exception:
            pass

        # Extract itemId and vendorItemId from page HTML
        try:
            if "page_content" not in locals():
                page_content = await self.page.content()
            
            # Extract itemId
            item_match = re.search(r'["\']?(?:originalI|i)temId["\']?\s*[:=]\s*["\']?(\d+)["\']?', page_content)
            if item_match:
                info["item_id"] = item_match.group(1)
            
            # Extract vendorItemId  
            vendor_match = re.search(r'["\']?(?:originalV|v)endorItemId["\']?\s*[:=]\s*["\']?(\d+)["\']?', page_content)
            if vendor_match:
                info["vendor_item_id"] = vendor_match.group(1)
        except Exception:
            pass

        return info

    def set_chunk_data_path(self, chunk_data_path: Optional[str]) -> None:
        new_path = (
            Path(chunk_data_path).expanduser()
            if chunk_data_path
            else self.DEFAULT_CHUNK_DATA_PATH
        )
        if new_path == self.chunk_data_path:
            return
        self.chunk_data_path = new_path
        self._chunk_dataset = None
