import os
import json
import pytesseract
from PIL import Image
from glob import glob

# ===== 설정 =====
BASE_DIR = "./data/outputs_structured"

# ===== 함수 =====
def ocr_image(image_path):
    """이미지 파일 경로를 받아 OCR 텍스트를 반환"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='kor+eng')  # 한글+영어
        return text.strip()
    except Exception as e:
        print(f"[ERROR] OCR failed for {image_path}: {e}")
        return ""

def process_all_directories(base_dir):
    """각 product_id 디렉토리의 images 폴더를 OCR하고 결과 저장"""
    subdirs = [d for d in glob(os.path.join(base_dir, "*")) if os.path.isdir(d)]

    for subdir in subdirs:
        product_id = os.path.basename(subdir)
        images_dir = os.path.join(subdir, "images")

        print(f"➡️ Checking {subdir}")
        if not os.path.exists(images_dir):
            print(f"❌ No images folder in {subdir}")
            continue  # images 폴더 없으면 스킵

        print(f"📂 Processing: {product_id}")
        image_files = sorted(
            [f for f in glob(os.path.join(images_dir, "*")) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        )

        ocr_results = []
        for img_path in image_files:
            text = ocr_image(img_path)
            ocr_results.append({
                "image_path": os.path.basename(img_path),
                "ocr_text": text
            })

        # JSON 파일 이름: ocrs_(product_id).json
        output_path = os.path.join(subdir, f"ocrs_{product_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ocr_results, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved OCR results → {output_path}")

# ===== 실행 =====
if __name__ == "__main__":
    process_all_directories(BASE_DIR)
