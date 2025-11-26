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
import logging
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)


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
        logger.warning("  ⚠️  이미지 디렉토리 없음: %s", images_dir)
        return []
    
    # 이미지 파일 찾기
    all_image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        all_image_files.extend(glob.glob(os.path.join(images_dir, ext)))
    
    if not all_image_files:
        logger.warning("  ⚠️  이미지 파일 없음")
        return []
    
    # btf_ 필터링
    if only_btf:
        image_files = [f for f in all_image_files if Path(f).name.startswith('btf_')]
        logger.info("  🔍 필터링: 전체 %d개 → BTF %d개", len(all_image_files), len(image_files))
        
        if not image_files:
            logger.warning("  ⚠️  btf_ 이미지가 없습니다. --all-images 옵션을 사용하면 모든 이미지 처리")
            return []
    else:
        image_files = all_image_files
        logger.info("  📸 %d개 이미지 발견 (전체 처리)", len(image_files))
    
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
    
    logger.info("  ✅ 성공: %d개, ❌ 실패: %d개", success_count, fail_count)
    
    return results


def save_ocr_results(product_id, data_dir, results):
    """OCR 결과 저장"""
    product_dir = os.path.join(data_dir, product_id)
    output_file = os.path.join(product_dir, f'ocrs_{product_id}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info("  💾 저장 완료: %s", output_file)


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
            logger.error("  ❌ 에러: %s", e)
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


