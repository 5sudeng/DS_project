import json
import re
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 최대 청크 길이 (OCR 출력 및 긴 텍스트 필드에 적용)
MAX_TEXT_CHUNK_LENGTH = 200

class ContentChunker:
    """
    다양한 유형의 원시 데이터를 정의된 스키마에 따라 청크 단위로 처리하고 구조화하는 클래스입니다.
    """
    def __init__(self, max_chunk_length: int = MAX_TEXT_CHUNK_LENGTH):
        self.max_chunk_length = max_chunk_length
        self.all_chunks: List[Dict[str, Any]] = []

    def _generate_chunk_id(self, source_file: str, index: int) -> str:
        """청크 ID를 생성합니다."""
        # 파일 이름에서 확장자를 제거하고 ID의 접두사로 사용
        base_name = re.sub(r'\..*$', '', source_file)
        # 청크 ID는 생성되는 순서대로 부여하여 고유성을 확보
        return f"{base_name}_c{index:05d}"

    def _clean_and_chunk_text(self, text: str, source_file: str, index: int, chunk_name: str, source_type: str, min_length: int = 1) -> None:
        """
        텍스트에서 HTML 태그를 제거하고, 지정된 최대 길이에 따라 텍스트를 청크로 나눕니다.
        """
        # HTML <br/> 태그를 공백으로 대체하고, 그 외 태그를 제거합니다.
        cleaned_text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text).strip()
        
        # 리뷰 등 긴 텍스트 청킹을 위한 특수 마커 제거 (필요시)
        # 불필요한 마커 제거 (예: ⸻, ✅, ⭐️ 등)
        cleaned_text = re.sub(r'[\u2e00-\u2e7f\u2500-\u257f\u2580-\u259f\u25a0-\u25ff\u2600-\u26ff\u2700-\u27bf\u2b50-\u2b55\u2013\n\r\t]', ' ', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        if not cleaned_text:
            return

        # 청킹 전략 결정: 길이가 min_length보다 길거나 source_type이 REVIEW인 경우 길이 분할 적용
        if len(cleaned_text) > self.max_chunk_length or source_type == "REVIEW":
            # 100자 단위로 텍스트를 나눕니다.
            for i in range(0, len(cleaned_text), self.max_chunk_length):
                chunk_content = cleaned_text[i:i + self.max_chunk_length].strip()
                if chunk_content:
                    self._add_chunk(
                        source_file=source_file,
                        source_type=source_type,
                        content_type="TEXT",
                        text_content=chunk_content,
                        metadata={
                            "origin_field": chunk_name,
                            "original_length": len(text),
                            "chunk_index": i // self.max_chunk_length,
                            "chunk_strategy": f"LENGTH_SPLIT_{self.max_chunk_length}CHARS"
                        }
                    )
        else:
             # 짧은 텍스트는 하나의 청크로 처리 (필드 단위 청킹)
             self._add_chunk(
                source_file=source_file,
                source_type=source_type,
                content_type="TEXT",
                text_content=cleaned_text,
                metadata={"origin_field": chunk_name, "original_length": len(text), "chunk_strategy": "FIELD_UNIT"}
            )

    def _add_chunk(self, source_file: str, source_type: str, content_type: str, text_content: Optional[str], metadata: Dict[str, Any]) -> None:
        """최종 청크 리스트에 새로운 청크를 추가합니다."""
        # 이전에 추가된 청크 개수를 기반으로 고유 ID를 생성합니다.
        new_chunk_id = self._generate_chunk_id(source_file, len(self.all_chunks))

        new_chunk = {
            "source_file": source_file,
            "source_type": source_type,
            "chunk_id": new_chunk_id,
            "content_type": content_type,
            "text_content": text_content if text_content else None,
            "metadata": metadata
        }
        self.all_chunks.append(new_chunk)
        
    def process_html(self, file_path: str, html_content: str) -> None:
        """HTML 파일을 처리하여 상품 제목, 가격, 메타 설명 및 JSON-LD를 추출합니다."""
        logger.info("--- Processing %s (HTML / Content Extraction & Chunking) ---", file_path)
        
        # 1. 상품 제목 추출
        title_match = re.search(r'<h1 class="product-title.*?"><span class="twc-font-bold">(.*?)</span></h1>', html_content, re.DOTALL)
        if title_match:
            title_text = title_match.group(1).strip()
            self._clean_and_chunk_text(
                title_text, 
                file_path, 
                1, 
                "product_title", 
                source_type="HTML_STRUCTURE",
                min_length=1
            )
            
        # 2. 최종 가격 추출
        price_match = re.search(r'<div class="price-amount final-price-amount.*?">(.*?)</div>', html_content)
        if price_match:
            price_text = price_match.group(1).strip()
            self._clean_and_chunk_text(
                price_text, 
                file_path, 
                2, 
                "final_price_amount", 
                source_type="HTML_STRUCTURE",
                min_length=1
            )

        # 3. 상품 주요 속성 (ul > li 목록) 추출
        properties_match = re.search(r'<ul class="twc-ml-\[16px\]">(.*?)</ul>', html_content, re.DOTALL)
        if properties_match:
            list_items = re.findall(r'<li.*?>(.*?)</li>', properties_match.group(1), re.DOTALL)
            for i, item in enumerate(list_items):
                item_text = re.sub(r'<[^>]+>', '', item).strip() # li 내부의 HTML 태그 제거
                if item_text:
                    self._clean_and_chunk_text(
                        item_text, 
                        file_path, 
                        3 + i, 
                        "product_property", 
                        source_type="HTML_STRUCTURE",
                        min_length=5 # 너무 짧은 항목은 제외
                    )

        # 4. 메타 설명 추출
        meta_desc_match = re.search(r'<meta name="description" content="(.*?)"/>', html_content)
        if meta_desc_match:
            meta_desc_text = meta_desc_match.group(1).strip()
            self._clean_and_chunk_text(
                meta_desc_text,
                file_path,
                100, 
                "meta_description", 
                source_type="HTML_META",
                min_length=30 # 설명이 충분히 길 때만 청크
            )

        # 5. JSON-LD 메타데이터 추출 (유용한 정보만 필터링)
        json_ld_match = re.search(r'<script async="" src="product" type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL)
        if json_ld_match:
            try:
                # JSON 파싱
                json_ld_text = json_ld_match.group(1).strip()
                json_ld_data = json.loads(json_ld_text)
                
                # 유용한 정보만 추출 (이미지 URL 등 불필요한 데이터 제외)
                if json_ld_data.get("@type") == "Product":
                    filtered_data = {
                        "@type": "Product",
                        "sku": json_ld_data.get("sku"),
                        "name": json_ld_data.get("name"),
                        "brand": json_ld_data.get("brand"),
                        "offers": {},
                        "aggregateRating": json_ld_data.get("aggregateRating")
                    }
                    
                    # offers에서 가격 정보만 추출 (배송 정보 제외)
                    if "offers" in json_ld_data:
                        offers = json_ld_data["offers"]
                        filtered_data["offers"] = {
                            "price": offers.get("price"),
                            "priceCurrency": offers.get("priceCurrency"),
                            "priceSpecification": offers.get("priceSpecification"),
                            "availability": offers.get("availability")
                        }
                    
                    # 필터링된 JSON을 문자열로 변환
                    filtered_json_str = json.dumps(filtered_data, ensure_ascii=False, separators=(',', ':'))
                    
                    self._add_chunk(
                        source_file=file_path,
                        source_type="HTML_META",
                        content_type="JSON_LD",
                        text_content=filtered_json_str,
                        metadata={"origin_field": "json_ld_schema", "chunk_strategy": "FIELD_UNIT"}
                    )
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 원본 저장 (fallback)
                logger.warning("Failed to parse JSON-LD, storing original")
                json_ld_text = json_ld_match.group(1).replace('\n', '').replace('\r', '').strip()
                self._add_chunk(
                    source_file=file_path,
                    source_type="HTML_META",
                    content_type="JSON_LD",
                    text_content=json_ld_text,
                    metadata={"origin_field": "json_ld_schema", "chunk_strategy": "FIELD_UNIT"}
                )


    def process_quantity_json(self, file_path: str, data: List[Dict[str, Any]]) -> None:
        """수량 정보(가격, 옵션 등) JSON 파일을 처리합니다. (필드 단위 청킹)"""
        logger.info("--- Processing %s (Quantity Info / Field Unit Chunking) ---", file_path)
        
        if not data or not isinstance(data, list):
            return

        main_data = data[0]

        # 1. 캐시 적립 혜택
        cashback_list = main_data.get('cashBackSummary', {}).get('basicCashBackList', [])
        for i, item in enumerate(cashback_list):
            benefit = item.get('benefit', '')
            if benefit:
                self._clean_and_chunk_text(
                    benefit,
                    file_path,
                    i,
                    "cashBackSummary.basicCashBackList.benefit",
                    source_type="BENEFIT_INFO",
                    min_length=1
                )

        # 2. 배송 정보 설명
        delivery_desc = main_data.get('delivery', {}).get('descriptions', '')
        if delivery_desc:
             # 배송 정보는 HTML 포함이므로 클리닝 후 청크
            self._clean_and_chunk_text(
                delivery_desc,
                file_path,
                100, # 인덱스 구분을 위해 큰 값 부여
                "delivery.descriptions",
                source_type="DELIVERY_INFO",
                min_length=1
            )
        
        # 3. 가격 정보 요약
        price_info = main_data.get('price', {})
        if price_info:
            price_details = {
                "finalPrice": price_info.get("finalPrice"),
                "couponUnitPrice": price_info.get("couponUnitPrice"),
                "saleUnitPrice": price_info.get("saleUnitPrice")
            }
            # 가격 정보는 텍스트로 변환하여 청크
            price_text = f"최종 가격: {price_details.get('finalPrice')}원, 단위 가격: {price_details.get('couponUnitPrice')}"
            
            self._clean_and_chunk_text(
                price_text,
                file_path,
                200, 
                "price.summary",
                source_type="PRICE_INFO",
                min_length=1
            )


        # 4. 다른 옵션 리스트
        option_list_modules = [m for m in main_data.get('moduleData', []) if m.get('viewType') == 'PRODUCT_OPTION_TABLE_LIST_VIEW']
        
        if option_list_modules:
            option_list = option_list_modules[0].get('optionList', [])
            for i, option in enumerate(option_list):
                option_name = option.get('optionItemName', '')
                final_price = option.get('finalPrice', '')
                final_unit_price = option.get('finalUnitPrice', '')
                delivery_type = option.get('deliveryType', '3P')
                
                option_text = f"옵션: {option_name}, 가격: {final_price}, 단위가격: {final_unit_price}, 배송유형: {delivery_type}"
                
                self._clean_and_chunk_text(
                    option_text,
                    file_path,
                    300 + i,
                    "optionList.option",
                    source_type="OPTION_INFO",
                    min_length=1
                )


    def process_btf_json(self, file_path: str, data: Dict[str, Any], image_url_to_path: Dict[str, str] = None) -> None:
        """상품 상세 정보 (JSON) 파일을 처리합니다. (필드 단위 청킹 및 긴 텍스트 분할)"""
        logger.info("--- Processing %s (Product Detail / Field Unit & Length Chunking) ---", file_path)
        
        if image_url_to_path is None:
            image_url_to_path = {}
        
        # 1. 반품/교환 정보 (긴 텍스트 - HTML 포함)
        return_charge_text = data.get('returnPolicyVo', {}).get('vendorItemReturnNotice', {}).get('returnCharge', '')
        if return_charge_text:
            # return_charge_text는 긴 텍스트이므로 길이 분할을 시도합니다.
            self._clean_and_chunk_text(
                return_charge_text, 
                file_path, 
                0, 
                "returnPolicy.returnCharge",
                source_type="STRUCTURED_FIELD",
                min_length=1 
            )

        # 2. 배송 정보 (긴 텍스트 - HTML 포함)
        delivery_charge_text = data.get('returnPolicyVo', {}).get('vendorItemDeliveryNotice', {}).get('deliveryCharge', '')
        if delivery_charge_text:
            # delivery_charge_text는 긴 텍스트이므로 길이 분할을 시도합니다.
            self._clean_and_chunk_text(
                delivery_charge_text, 
                file_path, 
                1, 
                "deliveryPolicy.deliveryCharge",
                source_type="STRUCTURED_FIELD",
                min_length=1
            )
            
        # 3. 필수 표기 정보 (Key-Value 쌍 - 필드 단위 청킹)
        essentials = data.get('essentials', [])
        for i, item in enumerate(essentials):
            title = item.get('title', 'Unknown Title')
            description = item.get('description', '')
            # 필수 정보는 필드 단위로 청크합니다. (min_length가 1이므로 길이가 짧아도 분할하지 않고 하나의 청크로 저장)
            self._clean_and_chunk_text(
                description,
                file_path,
                i + 2, # 인덱스 충돌 방지 위해 +2 (위에서 0, 1 사용)
                "essentials",
                source_type="ESSENTIAL_INFO",
                min_length=1 
            )

        # 4. 상세 이미지 정보 (이미지 URL) - Add local path for multimodal RAG
        details = data.get('details', [])
        image_chunks = [d for d in details if d.get('contentType') == 'IMAGE_NO_SPACE']
        for i, img_data in enumerate(image_chunks):
            content_desc = img_data.get('vendorItemContentDescriptions', [{}])[0]
            image_url = content_desc.get('content', '')
            if image_url:
                # Normalize URL for lookup
                normalized_url = image_url if image_url.startswith('http') else f'https:{image_url}'
                local_path = image_url_to_path.get(normalized_url)
                
                metadata = {
                    "origin_field": "details", 
                    "image_url": image_url, 
                    "index": i, 
                    "chunk_strategy": "IMAGE_REFERENCE"
                }
                if local_path:
                    metadata["local_image_path"] = local_path
                
                self._add_chunk(
                    source_file=file_path,
                    source_type="PRODUCT_DETAIL",
                    content_type="IMAGE_URL",
                    text_content=None, # 텍스트 내용은 비워둠
                    metadata=metadata
                )

    def process_reviews(self, file_path: str, data: Dict[str, Any]) -> None:
        """상품 리뷰 파일을 처리합니다. (100자 길이 단위 청킹)"""
        logger.info("--- Processing %s (Reviews / %d-Char Chunking) ---", file_path, self.max_chunk_length)
        reviews = data.get('rData', {}).get('paging', {}).get('contents', [])

        for i, review in enumerate(reviews):
            content = review.get('content', '')
            review_id = review.get('reviewId')
            
            # 리뷰 제목을 내용 앞에 붙여서 청킹합니다.
            title = review.get('title', '').strip()
            # 제목과 내용을 합치고, 리뷰이므로 min_length에 관계없이 길이 분할을 시도합니다.
            full_text = f"제목: {title}. 내용: {content}" if title else content
            
            # 리뷰는 무조건 길이 분할을 시도하므로 min_length를 작게 설정 (혹시 모를 빈 문자열 방지)
            self._clean_and_chunk_text(
                full_text,
                file_path,
                i, 
                "review.content",
                source_type="REVIEW",
                min_length=1 
            )

    def process_inquiries(self, file_path: str, data: Dict[str, Any]) -> None:
        """상품 문의 파일을 처리합니다. (문의/답변 필드 단위 청킹)"""
        logger.info("--- Processing %s (Inquiries / Field Unit Chunking) ---", file_path)
        inquiries = data.get('success', {}).get('rData', {}).get('navigation', {}).get('contents', [])

        for i, inquiry in enumerate(inquiries):
            inquiry_id = inquiry.get('inquiryId')
            
            # 1. 문의 내용 (질문)
            question_content = inquiry.get('content', '').replace('\r\n', ' ').strip()
            if question_content:
                # 문의/답변은 내용이 길지 않으므로 필드 단위 청킹 (min_length를 높여 20자 미만은 제외)
                self._clean_and_chunk_text(
                    question_content,
                    file_path,
                    i, 
                    "inquiry.question",
                    source_type="INQUIRY_Q",
                    min_length=20
                )
            
            # 2. 답변 내용 (답변)
            comments = inquiry.get('comments', [])
            for j, comment in enumerate(comments):
                answer_content = comment.get('content', '').replace('\n', ' ').strip()
                if answer_content:
                    # 문의/답변은 내용이 길지 않으므로 필드 단위 청킹 (min_length를 높여 20자 미만은 제외)
                    self._clean_and_chunk_text(
                        answer_content,
                        file_path,
                        i, # 질문과 동일한 인덱스 사용
                        "inquiry.answer",
                        source_type="INQUIRY_A",
                        min_length=20
                    )


