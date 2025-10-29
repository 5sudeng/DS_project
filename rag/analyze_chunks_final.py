"""
Product 청크 분석 스크립트 - 최종 버전
실제 JSON 파일로 테스트 완료
"""
import json
import sys
import re
from pathlib import Path


def analyze_product_chunks(filepath):
    """제품 파일의 청크 생성 분석"""
    
    print("="*80)
    print(f"📦 파일: {filepath}")
    print("="*80)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 에러: {e}")
        return
    except Exception as e:
        print(f"❌ 파일 읽기 에러: {e}")
        return
    
    print(f"\n✅ JSON 파싱 성공")
    print(f"상품 ID: {data.get('productId')}")
    print(f"상품명: {data.get('productTitle')}")
    print(f"가격: {data.get('price', 0):,}원")
    
    chunks = []
    
    # Chunk 1: 기본 정보
    print("\n" + "="*80)
    print("📋 Chunk 1: 기본 정보 (basic)")
    print("="*80)
    
    basic_text = f"상품명: {data.get('productTitle', 'N/A')}"
    if data.get('brand'):
        basic_text += f"\n브랜드: {data.get('brand')}"
    basic_text += f"\n상품ID: {data.get('productId')}"
    
    print(basic_text)
    print(f"\n📏 길이: {len(basic_text)}자, {len(basic_text.split())}단어")
    chunks.append(("basic", basic_text))
    
    # Chunk 2: 가격 정보
    print("\n" + "="*80)
    print("💰 Chunk 2: 가격 정보 (price)")
    print("="*80)
    
    price_text = f"가격: {data.get('price', 0):,}원"
    if data.get('unitPrice'):
        price_text += f"\n개당 가격: {data.get('unitPrice'):,}원"
    if data.get('unitPriceDescription'):
        price_text += f"\n{data.get('unitPriceDescription')}"
    
    print(price_text)
    print(f"\n📏 길이: {len(price_text)}자, {len(price_text.split())}단어")
    chunks.append(("price", price_text))
    
    # Chunk 3: 배송 정보
    if data.get('delivery'):
        print("\n" + "="*80)
        print("🚚 Chunk 3: 배송 정보 (delivery)")
        print("="*80)
        
        delivery = data['delivery']
        delivery_parts = []
        
        if delivery.get('descriptions'):
            desc = re.sub(r'<[^>]+>', ' ', str(delivery.get('descriptions', '')))
            desc = ' '.join(desc.split())
            delivery_parts.append(f"배송: {desc}")
        
        if delivery.get('type'):
            delivery_parts.append(f"배송 타입: {delivery.get('type')}")
        
        if delivery.get('speedType'):
            delivery_parts.append(f"배송 속도: {delivery.get('speedType')}")
        
        if delivery.get('countDownMessage'):
            msg = re.sub(r'<[^>]+>', ' ', str(delivery.get('countDownMessage', '')))
            msg = ' '.join(msg.split())
            if msg:
                delivery_parts.append(f"주문 마감: {msg}")
        
        delivery_text = "\n".join(delivery_parts) if delivery_parts else "배송 정보 없음"
        print(delivery_text)
        print(f"\n📏 길이: {len(delivery_text)}자, {len(delivery_text.split())}단어")
        chunks.append(("delivery", delivery_text))
    else:
        print("\n⚠️  배송 정보 없음")
    
    # Chunk 4: 옵션 정보
    if data.get('options'):
        print("\n" + "="*80)
        print("⚙️  Chunk 4: 옵션 정보 (options)")
        print("="*80)
        
        options_parts = ["구매 옵션:"]
        for i, opt in enumerate(data['options'][:5], 1):
            name = opt.get('optionItemName', 'N/A')
            price = opt.get('finalPrice', 'N/A')
            unit_price = opt.get('finalUnitPrice', '')
            
            opt_line = f"  {i}. {name}: {price}"
            if unit_price:
                opt_line += f" ({unit_price})"
            options_parts.append(opt_line)
        
        if len(data['options']) > 5:
            options_parts.append(f"  ... 외 {len(data['options'])-5}개 옵션")
        
        options_text = "\n".join(options_parts)
        print(options_text)
        print(f"\n📏 길이: {len(options_text)}자, {len(options_text.split())}단어")
        print(f"총 옵션 수: {len(data['options'])}개")
        chunks.append(("options", options_text))
    else:
        print("\n⚠️  옵션 정보 없음")
    
    # Chunk 5: 캐시백 정보
    if data.get('cashBackSummary', {}).get('basicCashBackList'):
        print("\n" + "="*80)
        print("💳 Chunk 5: 캐시백 정보 (cashback)")
        print("="*80)
        
        cb_list = data['cashBackSummary']['basicCashBackList']
        cb_parts = ["캐시백 혜택:"]
        for cb in cb_list:
            benefit = cb.get('benefit', 'N/A')
            amount = cb.get('amount', 0)
            validity = cb.get('validity', '')
            
            cb_line = f"  - {benefit}: {amount:,}원"
            if validity:
                cb_line += f" ({validity})"
            cb_parts.append(cb_line)
        
        cashback_text = "\n".join(cb_parts)
        print(cashback_text)
        print(f"\n📏 길이: {len(cashback_text)}자, {len(cashback_text.split())}단어")
        chunks.append(("cashback", cashback_text))
    else:
        print("\n⚠️  캐시백 정보 없음")
    
    # 요약
    print("\n" + "="*80)
    print("📊 청크 생성 요약")
    print("="*80)
    print(f"\n총 {len(chunks)}개 청크 생성:\n")
    
    total_chars = 0
    total_words = 0
    for chunk_type, chunk_text in chunks:
        char_count = len(chunk_text)
        word_count = len(chunk_text.split())
        total_chars += char_count
        total_words += word_count
        print(f"  [{chunk_type:12s}] {char_count:4d}자, {word_count:3d}단어")
    
    print(f"\n  {'총합':14s} {total_chars:4d}자, {total_words:3d}단어")
    
    # 추가 메타데이터
    print("\n" + "="*80)
    print("📋 기타 정보 (청크에 포함되지 않음)")
    print("="*80)
    
    metadata = []
    
    if data.get('reviewsSummary'):
        avg = data['reviewsSummary'].get('ratingAverage', 'N/A')
        count = data['reviewsSummary'].get('ratingCount', 0)
        metadata.append(f"리뷰: 평균 {avg}점, {count:,}개")
    
    if data.get('inquiries'):
        metadata.append(f"문의사항: {len(data['inquiries'])}개")
    
    if data.get('images'):
        if isinstance(data['images'], dict):
            atf = len(data['images'].get('fromATF', []))
            btf = len(data['images'].get('fromBTF', []))
            metadata.append(f"이미지: ATF {atf}개, BTF {btf}개")
    
    if data.get('optionsExpanded'):
        metadata.append(f"확장 옵션: {len(data['optionsExpanded'])}개")
    
    if data.get('btfFields'):
        btf_fields = data['btfFields']
        if btf_fields.get('detailContent'):
            metadata.append("상세 설명: 있음")
        if btf_fields.get('noticeContent'):
            metadata.append("공지사항: 있음")
    
    if metadata:
        for item in metadata:
            print(f"  - {item}")
    else:
        print("  없음")
    
    print("\n" + "="*80)
    print("✅ 분석 완료")
    print("="*80 + "\n")


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # 기본 경로
        filepath = "../data/outputs_structured/8826288636/product_8826288636.json"
    
    if not Path(filepath).exists():
        print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        print(f"\n사용법:")
        print(f"  python {sys.argv[0]} <파일경로>")
        print(f"\n예시:")
        print(f"  python {sys.argv[0]} ../data/outputs_structured/8826288636/product_8826288636.json")
        return
    
    analyze_product_chunks(filepath)


if __name__ == "__main__":
    main()
