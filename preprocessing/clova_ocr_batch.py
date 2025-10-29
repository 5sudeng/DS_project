"""
CLOVA OCR을 사용한 이미지 텍스트 추출 스크립트
- btf_ 이미지만 선택적으로 처리 가능 (비용 절감)
- 기존 Tesseract 방식을 대체합니다.
"""
import os
import json
import uuid
import time
import glob
import requests
from pathlib import Path
from tqdm import tqdm


class ClovaOCR:
    """네이버 CLOVA OCR"""
    
    def __init__(self, api_url, secret_key):
        self.api_url = api_url
        self.secret_key = secret_key
    
    def extract_text(self, image_path):
        """
        이미지에서 텍스트 추출
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            dict: {
                'success': bool,
                'texts': list,
                'full_text': str,
                'error': str (실패 시)
            }
        """
        try:
            # 이미지 포맷 추출
            ext = Path(image_path).suffix.lower().replace('.', '')
            if ext == 'jpg':
                ext = 'jpeg'
            
            # 요청 JSON 생성
            request_json = {
                'images': [{'format': ext, 'name': 'demo'}],
                'requestId': str(uuid.uuid4()),
                'version': 'V2',
                'timestamp': int(round(time.time() * 1000))
            }
            
            payload = {'message': json.dumps(request_json).encode('UTF-8')}
            
            # API 호출
            with open(image_path, 'rb') as f:
                files = [('file', f)]
                headers = {'X-OCR-SECRET': self.secret_key}
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    data=payload,
                    files=files,
                    timeout=30
                )
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'texts': [],
                    'full_text': '',
                    'error': f"API 오류: {response.status_code}"
                }
            
            result = response.json()
            
            # 텍스트 추출
            texts = []
            if 'images' in result:
                for image in result['images']:
                    if 'fields' in image:
                        for field in image['fields']:
                            texts.append(field['inferText'])
            
            return {
                'success': True,
                'texts': texts,
                'full_text': ' '.join(texts),
                'error': None
            }
            
        except FileNotFoundError:
            return {
                'success': False,
                'texts': [],
                'full_text': '',
                'error': 'File not found'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'texts': [],
                'full_text': '',
                'error': f'Request error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'texts': [],
                'full_text': '',
                'error': f'Unknown error: {str(e)}'
            }


def process_product_images(product_id, data_dir, ocr, delay=0.5, only_btf=True):
    """
    특정 제품의 이미지들을 OCR 처리
    
    Args:
        product_id: 제품 ID
        data_dir: 데이터 디렉토리
        ocr: ClovaOCR 인스턴스
        delay: API 호출 간 대기 시간 (초)
        only_btf: True이면 btf_로 시작하는 이미지만 처리 (기본값)
    
    Returns:
        list: OCR 결과 리스트
    """
    product_dir = os.path.join(data_dir, product_id)
    images_dir = os.path.join(product_dir, 'images')
    
    if not os.path.exists(images_dir):
        print(f"  ⚠️  이미지 디렉토리 없음: {images_dir}")
        return []
    
    # 이미지 파일 찾기
    all_image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        all_image_files.extend(glob.glob(os.path.join(images_dir, ext)))
    
    if not all_image_files:
        print(f"  ⚠️  이미지 파일 없음")
        return []
    
    # btf_ 필터링
    if only_btf:
        image_files = [f for f in all_image_files if Path(f).name.startswith('btf_')]
        print(f"  🔍 필터링: 전체 {len(all_image_files)}개 → BTF {len(image_files)}개")
        
        if not image_files:
            print(f"  ⚠️  btf_ 이미지가 없습니다. --all-images 옵션을 사용하면 모든 이미지 처리")
            return []
    else:
        image_files = all_image_files
        print(f"  📸 {len(image_files)}개 이미지 발견 (전체 처리)")
    
    results = []
    success_count = 0
    fail_count = 0
    
    for image_path in tqdm(image_files, desc="  OCR 처리중"):
        result = ocr.extract_text(image_path)
        
        if result['success']:
            success_count += 1
            results.append({
                'image_path': image_path,
                'image_name': Path(image_path).name,
                'ocr_text': result['full_text'],
                'ocr_texts': result['texts'],
                'success': True
            })
        else:
            fail_count += 1
            results.append({
                'image_path': image_path,
                'image_name': Path(image_path).name,
                'ocr_text': '',
                'ocr_texts': [],
                'success': False,
                'error': result['error']
            })
        
        # API 호출 제한 방지
        time.sleep(delay)
    
    print(f"  ✅ 성공: {success_count}개, ❌ 실패: {fail_count}개")
    
    return results


def save_ocr_results(product_id, data_dir, results):
    """OCR 결과 저장"""
    product_dir = os.path.join(data_dir, product_id)
    output_file = os.path.join(product_dir, f'ocrs_{product_id}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 저장 완료: {output_file}")


def process_all_products(data_dir, api_url, secret_key, delay=0.5, only_btf=True):
    """모든 제품 OCR 처리"""
    
    # 제품 디렉토리 찾기
    product_dirs = glob.glob(os.path.join(data_dir, "*/"))
    product_ids = [Path(d).name for d in product_dirs]
    
    print(f"\n{'='*80}")
    print(f"총 {len(product_ids)}개 제품 발견")
    if only_btf:
        print(f"모드: BTF 이미지만 처리 (비용 절감)")
    else:
        print(f"모드: 모든 이미지 처리")
    print(f"{'='*80}\n")
    
    # OCR 인스턴스 생성
    ocr = ClovaOCR(api_url, secret_key)
    
    # 통계
    total_images = 0
    total_success = 0
    total_fail = 0
    
    for idx, product_id in enumerate(product_ids, 1):
        print(f"\n[{idx}/{len(product_ids)}] 제품: {product_id}")
        print("-" * 80)
        
        try:
            results = process_product_images(product_id, data_dir, ocr, delay, only_btf)
            
            if results:
                save_ocr_results(product_id, data_dir, results)
                
                # 통계 업데이트
                total_images += len(results)
                total_success += sum(1 for r in results if r['success'])
                total_fail += sum(1 for r in results if not r['success'])
            
        except Exception as e:
            print(f"  ❌ 에러: {e}")
            continue
    
    # 최종 요약
    print(f"\n{'='*80}")
    print(f"📊 최종 통계")
    print(f"{'='*80}")
    print(f"총 제품 수: {len(product_ids)}개")
    print(f"총 이미지: {total_images}개")
    if total_images > 0:
        print(f"성공: {total_success}개 ({total_success/total_images*100:.1f}%)")
        print(f"실패: {total_fail}개")
    else:
        print(f"처리된 이미지 없음")
    print(f"{'='*80}\n")


def process_single_product(product_id, data_dir, api_url, secret_key, delay=0.5, only_btf=True):
    """단일 제품 OCR 처리"""
    
    print(f"\n{'='*80}")
    print(f"제품 {product_id} OCR 처리")
    if only_btf:
        print(f"모드: BTF 이미지만 처리")
    else:
        print(f"모드: 모든 이미지 처리")
    print(f"{'='*80}\n")
    
    ocr = ClovaOCR(api_url, secret_key)
    results = process_product_images(product_id, data_dir, ocr, delay, only_btf)
    
    if results:
        save_ocr_results(product_id, data_dir, results)
        
        # 결과 미리보기
        print(f"\n{'='*80}")
        print(f"📄 결과 미리보기 (최대 3개)")
        print(f"{'='*80}\n")
        
        for i, result in enumerate(results[:3], 1):
            print(f"[{i}] {result['image_name']}")
            if result['success']:
                preview = result['ocr_text'][:100]
                print(f"    {preview}{'...' if len(result['ocr_text']) > 100 else ''}")
            else:
                print(f"    ❌ {result.get('error', 'Unknown error')}")
            print()
    
    print("완료!")


def preview_filter(data_dir, product_id=None):
    """필터링 효과 미리보기"""
    if product_id:
        product_ids = [product_id]
    else:
        product_dirs = glob.glob(os.path.join(data_dir, "*/"))
        product_ids = [Path(d).name for d in product_dirs]
    
    print(f"\n{'='*80}")
    print(f"BTF 필터링 미리보기")
    print(f"{'='*80}\n")
    
    total_all = 0
    total_btf = 0
    
    for pid in product_ids[:10]:  # 최대 10개만
        images_dir = os.path.join(data_dir, pid, 'images')
        if not os.path.exists(images_dir):
            continue
        
        all_images = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            all_images.extend(glob.glob(os.path.join(images_dir, ext)))
        
        btf_images = [f for f in all_images if Path(f).name.startswith('btf_')]
        
        print(f"{pid}: 전체 {len(all_images)}개 → BTF {len(btf_images)}개")
        
        total_all += len(all_images)
        total_btf += len(btf_images)
    
    if total_all > 0:
        saved_pct = (total_all - total_btf) / total_all * 100
        print(f"\n{'='*80}")
        print(f"예상 비용 절감: {saved_pct:.1f}% ({total_all - total_btf}/{total_all}개 제외)")
        print(f"{'='*80}\n")


def main():
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='CLOVA OCR을 사용한 이미지 텍스트 추출',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # BTF 이미지만 처리 (권장, 비용 절감)
  python clova_ocr_batch.py --product-id 8826288636
  
  # 모든 이미지 처리
  python clova_ocr_batch.py --product-id 8826288636 --all-images
  
  # 필터링 효과 미리보기
  python clova_ocr_batch.py --preview
  
  # 모든 제품 처리
  python clova_ocr_batch.py
        """
    )
    
    parser.add_argument('--data-dir', type=str, default='../data/outputs_structured',
                       help='데이터 디렉토리 경로')
    parser.add_argument('--product-id', type=str,
                       help='특정 제품 ID (지정하지 않으면 모든 제품 처리)')
    parser.add_argument('--api-url', type=str,
                       help='CLOVA OCR API URL (또는 환경변수 CLOVA_OCR_API_URL)')
    parser.add_argument('--secret-key', type=str,
                       help='CLOVA OCR Secret Key (또는 환경변수 CLOVA_OCR_SECRET_KEY)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='API 호출 간 대기 시간 (초, 기본값: 0.5)')
    parser.add_argument('--all-images', action='store_true',
                       help='모든 이미지 처리 (기본: btf_만 처리)')
    parser.add_argument('--list-products', action='store_true',
                       help='사용 가능한 제품 목록 출력')
    parser.add_argument('--preview', action='store_true',
                       help='필터링 효과 미리보기 (API 호출 없음)')
    
    args = parser.parse_args()
    
    # 제품 목록 출력
    if args.list_products:
        product_dirs = glob.glob(os.path.join(args.data_dir, "*/"))
        product_ids = sorted([Path(d).name for d in product_dirs])
        print(f"\n사용 가능한 제품 ({len(product_ids)}개):")
        for pid in product_ids:
            print(f"  - {pid}")
        print()
        return
    
    # 필터링 미리보기
    if args.preview:
        preview_filter(args.data_dir, args.product_id)
        return
    
    # API 정보 확인
    api_url = args.api_url or os.getenv('CLOVA_OCR_API_URL')
    secret_key = args.secret_key or os.getenv('CLOVA_OCR_SECRET_KEY')
    
    if not api_url or not secret_key:
        print("❌ API URL과 Secret Key가 필요합니다.")
        print("\n옵션 1: 명령줄 인자")
        print("  python clova_ocr_batch.py --api-url YOUR_URL --secret-key YOUR_KEY")
        print("\n옵션 2: .env 파일에 추가")
        print("  CLOVA_OCR_API_URL=your_url")
        print("  CLOVA_OCR_SECRET_KEY=your_key")
        return
    
    # only_btf 설정 (--all-images 플래그의 반대)
    only_btf = not args.all_images
    
    # OCR 처리
    if args.product_id:
        # 특정 제품
        process_single_product(
            args.product_id,
            args.data_dir,
            api_url,
            secret_key,
            args.delay,
            only_btf
        )
    else:
        # 모든 제품
        process_all_products(
            args.data_dir,
            api_url,
            secret_key,
            args.delay,
            only_btf
        )


if __name__ == "__main__":
    main()
