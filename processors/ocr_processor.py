"""
OpenAI GPT-4o Vision-based OCR Processor.
"""
import base64
import json
import logging
import os
import time
import glob
from pathlib import Path
from typing import Any, Dict, List, Optional
from tqdm import tqdm

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIOCR:
    """OCR implementation using OpenAI GPT-4o Vision."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image using GPT-4o Vision.
        """
        try:
            base64_image = self._encode_image(image_path)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image. Output only the extracted text, preserving the layout as much as possible. If there is no text, return an empty string.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )
            
            content = response.choices[0].message.content
            return {
                "success": True,
                "full_text": content,
                "texts": content.split('\n') if content else [],
                "error": None
            }

        except Exception as e:
            logger.error(f"OpenAI OCR failed for {image_path}: {e}")
            return {
                "success": False,
                "full_text": "",
                "texts": [],
                "error": str(e)
            }

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")


class OCRProcessor:
    """OCR processing manager using OpenAI."""

    def __init__(self, api_key: Optional[str] = None, delay: float = 1.0):
        self.ocr = OpenAIOCR(api_key=api_key)
        self.delay = delay

    def process_product_images(self, product_id: str, data_dir: str, only_btf: bool = True) -> List[Dict[str, Any]]:
        """Process images for a specific product in parallel."""
        product_dir = os.path.join(data_dir, product_id)
        
        # Standard structure from artifacts.py:
        # run_dir/btf/images
        images_dir = os.path.join(data_dir, "btf", "images")
        if not os.path.exists(images_dir):
            # Fallback to old structure if needed or check direct path
            images_dir = os.path.join(data_dir, "images")
            
        if not os.path.exists(images_dir):
            logger.warning("  ⚠️  Image directory not found: %s", images_dir)
            return []

        # Find image files
        all_image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
            all_image_files.extend(glob.glob(os.path.join(images_dir, ext)))
        
        if not all_image_files:
            logger.warning("  ⚠️  No image files found in %s", images_dir)
            return []
        
        # Filter BTF images
        if only_btf:
            image_files = [f for f in all_image_files if Path(f).name.startswith('btf_')]
            logger.info("  🔍 Filtering: Total %d -> BTF %d", len(all_image_files), len(image_files))
            
            if not image_files:
                logger.warning("  ⚠️  No 'btf_' images found.")
                return []
        else:
            image_files = all_image_files
            logger.info("  📸 Found %d images (processing all)", len(image_files))
        
        results = []
        success_count = 0
        fail_count = 0
        
        # Parallel processing
        import concurrent.futures
        
        logger.info("  🚀 Starting parallel OCR processing (workers=3)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Create a future for each image
            future_to_image = {executor.submit(self.ocr.extract_text, image_path): image_path for image_path in image_files}
            
            # Use tqdm to track progress as futures complete
            for future in tqdm(concurrent.futures.as_completed(future_to_image), total=len(image_files), desc="  Processing OCR (OpenAI)"):
                image_path = future_to_image[future]
                try:
                    result = future.result()
                    
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
                except Exception as exc:
                    logger.error(f"Image processing generated an exception: {exc}")
                    fail_count += 1
                    results.append({
                        'image_path': image_path,
                        'image_name': Path(image_path).name,
                        'ocr_text': '',
                        'ocr_texts': [],
                        'success': False,
                        'error': str(exc)
                    })
                
                # Small delay to avoid rate limits even with parallelism
                time.sleep(self.delay / 3.0)
        
        # Sort results by filename to maintain order
        results.sort(key=lambda x: x['image_name'])
        
        logger.info("  ✅ Success: %d, ❌ Failed: %d", success_count, fail_count)
        return results

    def save_results(self, product_id: str, data_dir: str, results: List[Dict[str, Any]]) -> None:
        """Save OCR results to JSON."""
        # Save to run_dir directly or a specific output folder
        output_file = os.path.join(data_dir, f'ocrs_{product_id}.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info("  💾 Saved OCR results to: %s", output_file)
