import json
import re
import os
from typing import List, Dict, Any, Optional

# 최대 청크 길이 (OCR 출력 및 긴 텍스트 필드에 적용)
MAX_TEXT_CHUNK_LENGTH = 200

class DataChunker:
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
        print(f"--- Processing {file_path} (HTML / Content Extraction & Chunking) ---")
        
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

        # 5. JSON-LD 메타데이터 추출 (JSON 구조를 그대로 저장)
        json_ld_match = re.search(r'<script async="" src="product" type="application/ld\+json">(.*?)</script>', html_content, re.DOTALL)
        if json_ld_match:
            # HTML 엔티티를 디코딩하고 JSON 청크로 추가 (텍스트로 저장)
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
        print(f"--- Processing {file_path} (Quantity Info / Field Unit Chunking) ---")
        
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


    def process_btf_json(self, file_path: str, data: Dict[str, Any]) -> None:
        """상품 상세 정보 (JSON) 파일을 처리합니다. (필드 단위 청킹 및 긴 텍스트 분할)"""
        print(f"--- Processing {file_path} (Product Detail / Field Unit & Length Chunking) ---")
        
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

        # 4. 상세 이미지 정보 (이미지 URL)
        details = data.get('details', [])
        image_chunks = [d for d in details if d.get('contentType') == 'IMAGE_NO_SPACE']
        for i, img_data in enumerate(image_chunks):
            content_desc = img_data.get('vendorItemContentDescriptions', [{}])[0]
            image_url = content_desc.get('content', '')
            if image_url:
                self._add_chunk(
                    source_file=file_path,
                    source_type="PRODUCT_DETAIL",
                    content_type="IMAGE_URL",
                    text_content=None, # 텍스트 내용은 비워둠
                    metadata={"origin_field": "details", "image_url": image_url, "index": i, "chunk_strategy": "IMAGE_REFERENCE"}
                )

    def process_reviews(self, file_path: str, data: Dict[str, Any]) -> None:
        """상품 리뷰 파일을 처리합니다. (100자 길이 단위 청킹)"""
        print(f"--- Processing {file_path} (Reviews / {self.max_chunk_length}-Char Chunking) ---")
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
        print(f"--- Processing {file_path} (Inquiries / Field Unit Chunking) ---")
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


def main():
    # --- 파일 이름 정의 ---
    BTF_FILE = 'btf_86564_i175470_v3000104081_1761547265549.json'
    REVIEW_FILE = 'review_86564_p1_1761179851768.json'
    INQUIRY_FILE = 'inquiries_86564_p1_1761131645429.json'
    QUANTITY_FILE = 'quantity_info_86564_1761131830695.json'
    HTML_FILE = 'response_86564.html' # HTML 파일 이름 추가

    # --- 파일 내용 (이전에 추출된 JSON 텍스트 및 HTML) ---
    btf_data = {
      "rollbackInterstellar": False, "productId": 86564, "itemId": 175470, "vendorItemId": 3000104081,
      "returnPolicyVo": {
        "vendorItemReturnPolicyLayoutType": "RETAIL",
        "vendorItemReturnNotice": {
          "returnCharge": "ㆍ와우멤버십 회원: 무료로 반품/교환 가능<br/>ㆍ와우멤버십 회원 아닌 경우:<br/>1) [총 주문금액] - [반품 상품금액] = 19,800원 미만인 경우 반품비 5,000원<br/>2) [총 주문금액] - [반품 상품금액] = 19,800원 이상인 경우 반품비 2,500원"
        },
        "vendorItemDeliveryNotice": {
          "supportSameDayFresh": True,
          "deliveryCharge": "무료배송<br/>- 로켓배송 상품 중 19,800원 이상 구매 시 무료배송<br/>- 도서산간 지역 추가비용 없음"
        }
      },
      "essentials": [
        {"description": "컨텐츠 참조", "title": "제품명"},
        {"description": "소비기한(또는 유통기한) : 2026년 01월 28일 이거나 그 이후인 상품", "title": "제조연월일, 소비기한 또는 품질유지기한"},
        {"description": "86g x 6개", "title": "포장단위별 내용물의 용량(중량), 수량"},
        {"description": "컨텐츠 참조 ", "title": "영양성분"}
      ],
      "details": [
        {"cssClass": "type-IMAGE_NO_SPACE", "vendorItemContentDescriptions": [{"content": "//thumbnail.coupangcdn.com/thumbnails/remote/q89/image/retail/images/1546850209605462-9375cd0f-2bbe-4d17-8397-5013370c1e5c.jpg", "detailType": "IMAGE"}]},
        {"cssClass": "type-IMAGE_NO_SPACE", "vendorItemContentDescriptions": [{"content": "//thumbnail.coupangcdn.com/thumbnails/remote/q89/image/retail/images/988658446518196-061e0602-31cd-4689-8040-3f9629e260e7.jpg", "detailType": "IMAGE"}]},
      ]
    }

    review_data = {
      "rData": {
        "paging": {
          "contents": [
            {
              "reviewId": 782740950,
              "title": "",
              "content": "외관 패키지부터 익숙한 사발면 감성 그대로임. 빨간색 바탕에 ‘김치사발면’ 딱 적혀 있어서 딱 봐도 클래식한 컵라면 느낌. 6개 묶음 포장이라 캠핑이나 사무실 비치용으로 딱 좋음. 사이즈는 일반 큰사발보다 살짝 작고, 컵라면 중간 크기라 간식용으로 적당함. 뚜껑 재질도 두꺼워서 물 붓고 덮었을 때 찢어지지 않고 안정적임. ⸻ 조리법 조리법은 진짜 간단함. 뜨거운 물만 있으면 끝. 표시선까지 물 붓고 3분 기다리면 완성. 면이 얇아서 빨리 익고, 물 붓고 나서 김치향이 바로 올라옴. 면 불 조절하기도 쉬워서 바쁜 아침이나 간단한 야식으로 좋음. 뜨거운 물만 부어도 충분하지만, 끓는 물로 하면 더 깊은 맛이 살아남. 개인적으로는 전자레인지 30초 돌리면 국물 맛이 더 진해짐. ⸻ 맛 이게 왜 꾸준히 팔리는지 알겠음. 진짜 클래식한 김치라면의 정석. 국물은 칼칼하고 시원한 편인데, 맵다기보단 깔끔하게 톡 쏘는 김치 맛이 살아있음. 김치 건더기가 꽤 실해서 식감도 괜찮고, 밥 말아 먹으면 완벽함. 짜지 않고, 적당히 산미 있는 김치국 느낌이라 느끼하지 않음. 다른 컵라면처럼 자극적이지 않고 부담 없이 후루룩 먹기 좋음. ⸻ 양 86g이라 양은 많지 않음. 한 끼 식사라기보단 간식, 혹은 점심 후 입가심용으로 딱. 하지만 면이 얇고 후루룩 넘어가서 속은 편함. 컵라면 치고는 건더기도 꽤 들어 있고, 국물이 시원해서 만족감은 있음. 양이 아쉬운 사람은 김밥이나 삼각김밥이랑 같이 먹으면 딱 맞음. ⸻ 활용도 출근길에, 야근 중에, 캠핑 가서, 여행 가서 어디서든 편하게 먹을 수 있음. 전자레인지나 가스버너 없어도 물만 있으면 되니까 활용도 최고. 집에서는 김치사발면에 달걀 넣거나, 떡 조금 넣으면 훨씬 든든해짐. 개인적으로는 라면 위에 김가루 살짝 뿌리면 진짜 맛있음. ⸻ 총평 김치사발면은 신제품의 화려함보다 ‘익숙함’이 강점인 제품임. 먹을 때마다 “이 맛이야” 하게 되는 추억의 맛. 매운 거 잘 못 먹는 사람도 부담 없이 즐길 수 있고, 국물까지 시원하게 마무리 가능. 간단하면서도 만족도 높은 컵라면 찾는 분들께 강력 추천. 꾸준히 찾게 되는 이유가 확실함. 라면계의 국민 간식 그 자체임."
            },
            {
              "reviewId": 779711246,
              "title": "칼칼하고 시원한 김치 국물 + 간편 조리 + 부담 없는",
              "content": "1. 시원하고 칼칼한 김치 국물 맛\n\t•\t여러 리뷰들이 “김치 맛이 잘 살아 있다”, “국물이 개운하다”는 표현을 많이 쓰더군요.  ￼\n\t•\t특히 매운 정도나 짭조름함이 과하지 않고, 김치의 새콤함과 매콤함이 적절히 조화를 이루어 먹고 나서도 깔끔한 뒷맛이 남는다는 후기들이 많아요.  ￼\n\t•\t해장용 혹은 속 풀이용으로도 괜찮다는 표현이 종종 보이는데, 자극적이지 않으면서도 입맛을 돋우는 맛이라는 평가가 강점으로 꼽힙니다."
            }
          ]
        }
      }
    }

    inquiry_data = {
      "success": {
        "rData": {
          "navigation": {
            "contents": [
              {
                "vendorItemId": 89819605191,
                "inquiryId": 144105194,
                "content": "10/9일부터 상품이 움직이지 않고 있어요 확인하여 조치하여 주세요",
                "comments": [{"inquiryCommentId": 137607382, "displayWriter": "탑몰", "content": "판매자입니다. 고객님께서 주신 문의 글이 주문번호로 인입되지 않아 주문내역을 확인할수가 없습니다. 주문번호로 재문의 주시면 확인해드리겠습니다."}]
              },
              {
                "vendorItemId": 93085331442,
                "inquiryId": 142520704,
                "content": "더 작은사이즈도 있나요?",
                "comments": [{"inquiryCommentId": 135993141, "displayWriter": "장바구니닷컴", "content": "더 작은사이즈는 없습니다~~"}]
              }
            ]
          }
        }
      }
    }
    
    # quantity_info_86564_1761131830695.json 데이터
    quantity_data = [
      {
        "abFlags": {"applyExtremeProminenceFreeDeliveryMessages": "A", "ab54632": "B"},
        "appliedCoupon": None,
        "benefitDisplayType": None,
        "bundleOption": {"optionDetails": None, "options": [], "viewType": None},
        "cashBackSummary": {
          "basicCashBackList": [{"amount": 55, "benefit": "쿠페이 머니 결제 시 1% 적립", "expired": False, "i18nAmount": {"amount": "55", "currency": "KRW", "fractionDigits": 0, "rawAmount": 55}, "leftDays": None, "rate": "1", "type": "BASIC", "validity": "월 최대 1만원"}],
          "finalCashBackAmt": 55
        },
        "delivery": {
          "descriptions": "<em class='prod-txt-onyx prod-txt-green-2'>내일(목) 10/23</em><em class='prod-txt-onyx  prod-txt-green-normal'> 도착 보장</em><em class='prod-txt-onyx'> (</em><em class='prod-txt-onyx'>3시간 42분</em><em class='prod-txt-onyx'> 내 주문 시)</em>",
          "type": "ROCKET_DELIVERY"
        },
        "moduleData": [
          {
            "detailPriceBundle": {
              "finalPrice": {
                "price": 5470,
                "unitPriceDescription": "(1개당 912원)",
              }
            },
            "viewType": "PRODUCT_DETAIL_PRICE_INFO",
          },
          {
            "landingItemId": 175470,
            "optionList": [
              { "optionItemName": "1개", "finalPrice": "1,050원", "finalUnitPrice": "1개당 1,050원", "deliveryType": None },
              { "optionItemName": "6개", "finalPrice": "5,470원", "finalUnitPrice": "1개당 912원", "deliveryType": "ROCKET" },
              { "optionItemName": "12개", "finalPrice": "10,780원", "finalUnitPrice": "1개당 898원", "deliveryType": "ROCKET" },
              { "optionItemName": "24개", "finalPrice": "19,700원", "finalUnitPrice": "1개당 821원", "deliveryType": "ROCKET" }
            ],
            "viewType": "PRODUCT_OPTION_TABLE_LIST_VIEW"
          }
        ],
        "price": {
          "finalPrice": "5,470", "couponUnitPrice": "1개당 912원", "saleUnitPrice": "1개당 912원"
        },
      }
    ]
    
    # response_86564.html 데이터 (핵심 정보만 발췌하여 문자열로 정의)
    # 실제 HTML 전체 내용은 매우 길지만, 추출 로직 테스트를 위해 필요한 부분만 포함
    html_content = """
    <!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0"/>
    <meta name="description" content="현재 별점 4.8점, 리뷰 132816개를 가진 김치사발면 86g, 6개! 지금 쿠팡에서 더 저렴하고 다양한 컵라면 제품들을 확인해보세요."/>
    <title>김치사발면 86g, 6개 - 컵라면 | 쿠팡</title>
    <script async="" src="product" type="application/ld+json">{"@context":"https://schema.org/","@type":"Product","sku":"86564-175470","name":"김치사발면 86g, 6개","offers":{...},"aggregateRating":{"@type":"AggregateRating","ratingValue":4.8,"ratingCount":"132816"}}</script>
    </head><body><div class="sdp-content">
    <div class="twc-flex twc-justify-between twc-items-start"><div>
    <h1 class="product-title twc-text-lg twc-text-black"><span class="twc-font-bold">김치사발면 86g, 6개</span></h1>
    <div class="country-of-origin">원산지: 상품 상세설명 참조</div>
    </div></div>
    <div class="price-container">
    <div class="final-price twc-flex twc-items-center twc-flex-wrap">
    <div class="price-amount final-price-amount !twc-leading-[24px]">5,470원</div>
    <div><div class="final-unit-price">(1개당 912원)</div></div>
    </div></div>
    <div class="product-description twc-pt-[16px] twc-mb-[16px]"><ul class="twc-ml-[16px]">
    <li class="twc-list-disc twc-list-outside twc-text-[calc(var(--adjust-font-size)+12px)]">소비기한(또는 유통기한): 2025-12-11 이거나 그 이후인 상품</li>
    <li class="twc-list-disc twc-list-outside twc-text-[calc(var(--adjust-font-size)+12px)]">포장형태: 컵</li>
    <li class="twc-list-disc twc-list-outside twc-text-[calc(var(--adjust-font-size)+12px)]">라면 맛: 보통맛</li>
    </ul></div>
    </div></body></html>
    """

    
    # DataChunker 인스턴스 생성
    chunker = DataChunker()

    # 데이터 처리
    chunker.process_html(HTML_FILE, html_content) # HTML 파일 처리 로직
    chunker.process_btf_json(BTF_FILE, btf_data)
    chunker.process_reviews(REVIEW_FILE, review_data)
    chunker.process_inquiries(INQUIRY_FILE, inquiry_data)
    chunker.process_quantity_json(QUANTITY_FILE, quantity_data)
    
    # --- 청크 결과를 파일로 저장하는 로직 ---
    OUTPUT_DIR = '../exports_normalized'
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'chunked_data_output.json')
    
    # 출력 디렉토리가 없으면 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True) 

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(chunker.all_chunks, f, ensure_ascii=False, indent=4)
        print(f"\n[INFO] 청크 데이터가 성공적으로 파일에 저장되었습니다: {OUTPUT_FILE}")
    except Exception as e:
        print(f"\n[ERROR] 파일 저장 중 오류 발생: {e}")
    # -----------------------------------------------

    # 결과 출력 (기존 콘솔 출력)
    print("\n" + "="*80)
    print(f"Final Chunking Summary (Total {len(chunker.all_chunks)} Chunks):")
    print("="*80)

    # 상위 10개 청크 출력
    for i, chunk in enumerate(chunker.all_chunks[:15]):
        print(f"\n[{i+1}] Source: {chunk['source_file']}")
        print(f"    ID: {chunk['chunk_id']}")
        print(f"    Type: {chunk['source_type']} ({chunk['content_type']})")
        print(f"    Metadata: Strategy: {chunk['metadata'].get('chunk_strategy')}")
        # 긴 텍스트 청크는 내용 일부만 출력
        content_preview = chunk['text_content'][:77] + '...' if chunk['text_content'] and len(chunk['text_content']) > 80 else chunk['text_content']
        print(f"    Content: {content_preview}")

    print("\n... and more chunks.")
    print("="*80)

if __name__ == "__main__":
    main()
