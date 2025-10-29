# 제품별 RAG 시스템 (Product-Specific RAG)

쿠팡 상품 데이터를 활용한 검색 증강 생성(RAG) 시스템입니다. 제품 정보, 리뷰, OCR 텍스트, 이미지를 통합 검색하여 사용자 질문에 답변합니다.

## 🎯 주요 기능

- ✅ **제품별 벡터 스토어**: 각 제품마다 독립적인 FAISS 인덱스 구축
- ✅ **멀티모달 검색**: 텍스트(상품정보/리뷰/OCR) + 이미지(CLIP) 통합 검색
- ✅ **캐싱 시스템**: 한 번 구축한 벡터 스토어 재사용으로 빠른 로딩
- ✅ **자연어 변환**: JSON 구조를 자연어로 변환하여 검색 품질 향상
- ✅ **상세 결과 출력**: 검색 과정 및 결과를 단계별로 확인 가능
- ✅ **OpenAI 선택적 사용**: API 없이도 검색 기능만 사용 가능

## 📁 프로젝트 구조

```
DS_project/rag/
├── rag_with_detail.py          # 메인 RAG 시스템 (상세 출력 포함)
├── analyze_chunks_final.py     # 청크 생성 분석 도구
├── requirements_fixed.txt      # 필요한 패키지 목록
├── TROUBLESHOOTING.md         # 문제 해결 가이드
└── rag_cache_products/        # 벡터 스토어 캐시 디렉토리

data/outputs_structured/
├── 8826288636/                # 제품 ID별 디렉토리
│   ├── product_8826288636.json
│   ├── reviews_8826288636_*.jsonl
│   ├── ocrs_8826288636.json
│   └── images/
├── 487322/
└── ...
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# 가상환경 생성 (권장)
conda create -n rag_env python=3.11
conda activate rag_env

# 패키지 설치
pip install -r requirements_fixed.txt
```

**중요**: PyTorch 2.0+ 필요 (보안 취약점 해결)
```bash
pip install --upgrade torch>=2.0.0 torchvision
```

### 2. OpenAI API 키 설정 (선택사항)

```bash
# .env 파일 생성
echo "OPENAI_API_KEY=sk-your-api-key-here" > .env
```

또는

```bash
# 환경 변수 설정
export OPENAI_API_KEY=sk-your-api-key-here
```

## 📖 사용 방법

### 기본 사용

#### 1. 사용 가능한 제품 확인
```bash
python rag_with_detail.py --list-products
```

#### 2. 벡터 스토어 구축
```bash
# 특정 제품 구축
python rag_with_detail.py --build --product-id 8826288636

# 모든 제품 구축
python rag_with_detail.py --build

# 강제 재구축 (캐시 무시)
python rag_with_detail.py --build --product-id 8826288636 --force-rebuild
```

#### 3. 질문하기

**일반 모드 (OpenAI 사용)**
```bash
python rag_with_detail.py \
  --product-id 8826288636 \
  --query "이 상품의 가격은 얼마인가요?"
```

**검색 전용 모드 (OpenAI 없이)**
```bash
python rag_with_detail.py \
  --product-id 8826288636 \
  --query "가격은?" \
  --no-openai
```

**상세 결과 보기**
```bash
python rag_with_detail.py \
  --product-id 8826288636 \
  --query "가격은?" \
  --show-retrieval \
  --verbose \
  --no-openai
```

#### 4. 대화형 모드
```bash
python rag_with_detail.py --product-id 8826288636

# 대화 중 명령어:
# - detail: 검색 결과 상세 표시 ON/OFF
# - verbose: 더 자세한 출력 ON/OFF  
# - exit/quit/종료: 종료
```

### 고급 사용

#### 데이터 경로 지정
```bash
python rag_with_detail.py \
  --data-dir /path/to/outputs_structured \
  --cache-dir ./my_cache \
  --build --product-id 8826288636
```

#### 청크 분석
```bash
# 특정 제품의 청크 생성 과정 확인
python analyze_chunks_final.py ../data/outputs_structured/8826288636/product_8826288636.json
```

## 📊 출력 예시

### 기본 검색 결과
```
질문: 가격은?
제품: 8826288636

검색 완료:
  - 상품: 3개
  - 리뷰: 3개
  - OCR: 2개
  - 이미지: 3개

================================================================================
답변:
================================================================================
이 상품의 가격은 4,420원입니다. 개당 가격은 884원이며, 
5개 묶음 구매 시 4,420원, 10개는 7,630원, 25개는 18,350원입니다.
================================================================================
```

### 상세 검색 결과 (`--show-retrieval`)
```
================================================================================
검색 결과 상세
================================================================================

📦 상품 정보 (3개)
--------------------------------------------------------------------------------

[1] Score: 0.6234
Type: price
Content:
가격: 4420원
개당 가격: 884원
(1개당 884원)

[2] Score: 0.7123
Type: basic
Content:
상품명: 농심 얼큰한 너구리 120g
상품ID: 8826288636

[3] Score: 0.8456
Type: delivery
Content:
배송: 내일(목) 10/23 새벽 7시 전 도착 보장
배송 타입: ROCKET_DELIVERY
배송 속도: OVERNIGHT

⭐ 리뷰 (3개)
--------------------------------------------------------------------------------

[1] Score: 0.6543
Rating: 5점
Content:
평소 라면을 아주 좋아해서 자주 먹고 있는데...

🔍 OCR 텍스트 (2개)
--------------------------------------------------------------------------------

[1] Score: 0.9012
Content: 나트륨 1,760 mg 88%|탄수화물 83 g 26%...

🖼️  이미지 (3개)
--------------------------------------------------------------------------------

[1] Score: 12.3456
Path: ../data/outputs_structured/8826288636/images/1.png
```

## 🏗️ 시스템 아키텍처

### 데이터 처리 파이프라인

```
1. 데이터 로딩
   ├── Product JSON → 자연어 변환 → 5개 청크
   ├── Reviews JSONL → 리뷰 텍스트 추출
   ├── OCR JSON → OCR 텍스트 추출
   └── Images → CLIP 임베딩

2. 벡터화
   ├── 텍스트: sentence-transformers/all-MiniLM-L6-v2
   └── 이미지: openai/clip-vit-base-patch32

3. 인덱싱
   ├── FAISS (텍스트)
   └── FAISS (이미지)

4. 검색
   ├── 쿼리 임베딩
   ├── 유사도 계산 (코사인 유사도)
   └── Top-K 결과 반환

5. 생성 (선택)
   └── OpenAI GPT-4o-mini
```

### 청크 구조

각 제품은 5개의 청크로 분할됩니다:

| Chunk | Type | 내용 | 평균 길이 |
|-------|------|------|-----------|
| 1 | basic | 상품명, 브랜드, ID | ~40자 |
| 2 | price | 가격, 개당 가격 | ~35자 |
| 3 | delivery | 배송 정보, 타입, 속도 | ~70자 |
| 4 | options | 구매 옵션 (최대 5개) | ~70자 |
| 5 | cashback | 캐시백 혜택 | ~35자 |

**핵심 설계 원칙**: JSON 구조를 **자연어로 변환**하여 임베딩 품질 향상

```python
# Before (검색 안됨)
'{"price": 4420, "unitPrice": 884}'

# After (검색 잘됨)
'가격: 4420원\n개당 가격: 884원'
```

## 🔧 주요 파라미터

### 검색 파라미터
- `k=3`: 각 타입별 상위 3개 결과 반환
- 유사도 측정: L2 distance (FAISS)
- 정규화: 임베딩 벡터 정규화 적용

### 모델
- **텍스트 임베딩**: `sentence-transformers/all-MiniLM-L6-v2`
  - 차원: 384
  - 장점: 빠르고 안정적
  
- **이미지 임베딩**: `openai/clip-vit-base-patch32`
  - 차원: 512
  - 멀티모달: 텍스트-이미지 매칭

- **LLM**: `gpt-4o-mini` (선택)
  - Temperature: 0.7

## 🛠️ 문제 해결

### 자주 발생하는 문제

#### 1. 검색 결과가 0개
```bash
# 캐시 삭제 후 재구축
rm -rf ./rag_cache_products
python rag_with_detail.py --build --product-id 8826288636 --force-rebuild
```

#### 2. Torch 버전 에러
```bash
pip install --upgrade torch>=2.0.0 torchvision
```

#### 3. OpenAI 초기화 실패
```bash
# OpenAI 없이 사용
python rag_with_detail.py --no-openai --list-products
```

#### 4. 메모리 부족
```python
# CPU 모드 사용 (코드 수정)
model_kwargs={'device': 'cpu'}
```

자세한 내용은 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참고

## 📈 성능

### 벡터 스토어 구축 시간 (제품당)
- Product chunks: ~1초
- Reviews: ~3초 (30개 리뷰 기준)
- OCR: ~0.5초
- Images: ~2초 (7개 이미지 기준)
- **총**: ~7초/제품

### 검색 시간
- 텍스트 검색: ~0.1초
- 이미지 검색: ~0.2초
- LLM 답변 생성: ~2초

### 캐시 사용 시
- 로딩: ~0.5초
- 검색: ~0.1초

## 🔬 평가 예시 질문

### 상품 정보 관련
```bash
python rag_with_detail.py --product-id 8826288636 --query "가격은?"
python rag_with_detail.py --product-id 8826288636 --query "브랜드가 뭐야?"
python rag_with_detail.py --product-id 8826288636 --query "상품명은?"
```

### 배송 관련
```bash
python rag_with_detail.py --product-id 8826288636 --query "언제 배송되나요?"
python rag_with_detail.py --product-id 8826288636 --query "로켓배송인가요?"
```

### 옵션 관련
```bash
python rag_with_detail.py --product-id 8826288636 --query "몇 개씩 살 수 있나요?"
python rag_with_detail.py --product-id 8826288636 --query "10개 사면 얼마예요?"
```

### 리뷰 관련
```bash
python rag_with_detail.py --product-id 8826288636 --query "맛있나요?"
python rag_with_detail.py --product-id 8826288636 --query "후기 좀 알려줘"
```

## 📦 필수 패키지

```
langchain==0.3.7
langchain-community==0.3.5
langchain-openai==0.2.6
sentence-transformers==3.3.1
faiss-cpu==1.9.0
torch>=2.0.0
transformers>=4.40.0
openai==1.54.5
Pillow==11.0.0
python-dotenv==1.0.1
```

## 🤝 기여

이슈나 개선 사항이 있으면 자유롭게 제안해주세요!

## 📝 라이선스

이 프로젝트는 교육 목적으로 작성되었습니다.

## 📧 문의

문제가 발생하면:
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 확인
2. 에러 메시지와 함께 이슈 등록
3. `--show-retrieval --verbose` 옵션으로 상세 로그 확인

## 🎓 참고 자료

- [LangChain Documentation](https://python.langchain.com/)
- [FAISS Documentation](https://faiss.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [CLIP: OpenAI](https://github.com/openai/CLIP)

---

**마지막 업데이트**: 2024-10-29  
**버전**: 1.0.0  
**상태**: ✅ 프로덕션 준비 완료
