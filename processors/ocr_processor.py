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
from typing import Any, Dict, List
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


class OCRProcessor:
    """OCR processing manager."""

    def __init__(self, api_url: str, secret_key: str, delay: float = 0.5):
        self.ocr = ClovaOCR(api_url, secret_key)
        self.delay = delay

    def process_product_images(self, product_id: str, data_dir: str, only_btf: bool = True) -> List[Dict[str, Any]]:
        """Process images for a specific product."""
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
                logger.warning("  ⚠️  btf_ 이미지가 없습니다.")
                return []
        else:
            image_files = all_image_files
            logger.info("  📸 %d개 이미지 발견 (전체 처리)", len(image_files))
        
        results = []
        success_count = 0
        fail_count = 0
        
        for image_path in tqdm(image_files, desc="  OCR 처리중"):
            result = self.ocr.extract_text(image_path)
            
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
            
            time.sleep(self.delay)
        
        logger.info("  ✅ 성공: %d개, ❌ 실패: %d개", success_count, fail_count)
        return results

    def save_results(self, product_id: str, data_dir: str, results: List[Dict[str, Any]]) -> None:
        """Save OCR results to JSON."""
        product_dir = os.path.join(data_dir, product_id)
        output_file = os.path.join(product_dir, f'ocrs_{product_id}.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info("  💾 저장 완료: %s", output_file)


