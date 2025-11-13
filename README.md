# 🛍️ AI-Powered Coupang Shopping Assistant

LLM 기반 대화형 쿠팡 쇼핑 도우미 - Playwright를 사용한 실시간 상품 탐색 및 AI 기반 의도 파악

## 📋 목차

- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)
- [대화 흐름 예시](#대화-흐름-예시)
- [기술 스택](#기술-스택)
- [주요 모듈 설명](#주요-모듈-설명)

## 🎯 주요 기능

### 1. **AI 기반 의도 분류**
- OpenAI GPT를 사용한 사용자 발화 의도 자동 파악
- 만족/불만족/질문 자동 분류
- 룰 베이스가 아닌 LLM 기반 자연어 이해

### 2. **실시간 상품 정보 탐색**
- Playwright로 쿠팡 페이지 실시간 크롤링
- 리뷰 및 문의 섹션에서 키워드 매칭
- 사용자 질문에 대한 자동 답변 생성

### 3. **동적 검색 및 추천**
- 사용자 불만족 시 자동으로 새로운 상품 검색
- LLM이 생성한 최적화된 검색어로 검색
- 검색 결과에서 상품 선택 및 전환

### 4. **대화형 인터페이스**
- 티키타카 대화 지원
- 장바구니 담기 자동화
- 컨텍스트 기반 자연스러운 대화 흐름

## 📁 프로젝트 구조

```
DS_project/
├── agent/
│   ├── interactive_shopping_cli.py      # 메인 대화형 CLI
│   ├── llm_utils.py                     # LLM 의도 분류 및 검색어 생성
│   ├── coupang_playwright_agent.py      # 상품 페이지 탐색 에이전트
│   ├── coupang_search_agent.py          # 쿠팡 검색 에이전트
│   └── coupang_scenario_pipeline.py     # 배치 처리 파이프라인
├── crawling/
│   ├── fetch_html.py                    # HTML 페이지 가져오기
│   ├── review.py                        # 리뷰 데이터 수집
│   ├── inquiries.py                     # 문의 데이터 수집
│   └── quantity.py                      # 재고 정보 수집
└── rag/
    └── requirements.txt                 # 의존성 패키지
```

## 🔧 설치 방법

### 1. 환경 설정

```bash
# Python 3.11 권장
conda create -n dsproject python=3.11
conda activate dsproject
```

### 2. 의존성 설치

```bash
# 필수 패키지 설치
pip install playwright openai langchain langchain-openai
pip install beautifulsoup4 requests httpx
pip install python-dotenv

# Playwright 브라우저 설치
playwright install chromium
```

### 3. 환경 변수 설정

```bash
# OpenAI API 키 설정
export OPENAI_API_KEY="your-api-key-here"

# 또는 .env 파일 생성
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 4. 쿠키 파일 준비 (선택 사항)

쿠팡의 봇 방어를 우회하기 위해 쿠키 사용을 권장합니다:

1. Chrome 브라우저에서 쿠팡 로그인
2. F12 → Console 탭에서 실행:
   ```javascript
   copy(document.cookie)
   ```
3. `cookie.txt` 파일에 붙여넣기

## 🚀 사용 방법

### 대화형 모드 (추천)

```bash
# 쿠키 파일 사용 (권장)
python -m agent.interactive_shopping_cli --cookie-file cookie.txt

# 브라우저 보이게 실행 (디버깅용)
python -m agent.interactive_shopping_cli --cookie-file cookie.txt

# Headless 모드
python -m agent.interactive_shopping_cli --cookie-file cookie.txt --headless
```

### 배치 모드 (기존 시나리오)

```bash
python -m agent.coupang_scenario_pipeline \
  --url "https://www.coupang.com/vp/products/8668543035" \
  --question "발볼 넓은 사람도 신을 수 있대?" \
  --follow-up "맘에 안들어" \
  --cookie-file cookie.txt \
  --headless \
  --collect-quantity
```

## 💬 대화 흐름 예시

```
🛍️  쿠팡 쇼핑 도우미에 오신 것을 환영합니다!

📦 상품 URL을 입력하세요: https://www.coupang.com/vp/products/8668543035
✓ 상품: 나이키 에어맥스 운동화

❓ 무엇이 궁금하신가요?

💬 > 발볼 넓은 사람도 신을 수 있을까?
[의도 파악: question (신뢰도: 0.95)]
⏳ 리뷰와 문의를 확인하는 중...

🤖 구매 후기에서 '발볼이 넓어도 편하게 맞는다'는 평가가 있었습니다.
   대부분 정사이즈를 추천하고 있습니다.

💡 이 상품이 마음에 드시나요? 장바구니에 담아드릴까요? (예/아니오)

💬 > 너무 비싸. 좀 더 저렴한 걸로
[의도 파악: dissatisfied (신뢰도: 0.92)]

🔍 이해했습니다: 가격이 너무 비싸다
   새로운 상품을 찾아보겠습니다...

💡 검색어: '운동화 발볼 넓은 저렴한 가성비'

🔍 검색 중: '운동화 발볼 넓은 저렴한 가성비'
✓ 5개 상품 발견

📦 검색 결과:
1. 뉴발란스 530 운동화
   가격: 45,900원

2. 아디다스 경량 운동화
   가격: 39,000원

3. 푸마 런닝화
   가격: 42,000원

🔢 원하는 상품의 번호를 입력하세요 (1-5):

💬 > 2
✓ 선택: 아디다스 경량 운동화
⏳ 상품 페이지를 불러오는 중...
```

## 🛠 기술 스택

### Core Technologies
- **Python 3.11**: 메인 언어
- **Playwright**: 브라우저 자동화 및 동적 페이지 크롤링
- **OpenAI GPT-4**: 의도 분류 및 자연어 처리
- **LangChain**: LLM 워크플로우 관리

### Web Scraping & Data
- **BeautifulSoup4**: HTML 파싱
- **httpx/requests**: HTTP 요청 처리
- **asyncio**: 비동기 I/O 처리

### Anti-Detection
- JavaScript injection으로 `navigator.webdriver` 숨김
- 실제 Chrome과 동일한 User-Agent 및 헤더
- 쿠키 기반 세션 관리
- Akamai 봇 방어 우회 전략

## 📚 주요 모듈 설명

### 1. `interactive_shopping_cli.py`
**메인 대화형 인터페이스**

- 사용자와의 실시간 대화 처리
- Playwright 브라우저 세션 관리
- 상품 페이지 로딩 및 상태 관리
- 쿠키 로딩 및 안티봇 설정

```python
cli = InteractiveShoppingCLI(
    headless=False,
    cookie_file="cookie.txt",
    api_key="your-api-key"
)
await cli.run()
```

### 2. `llm_utils.py`
**LLM 기반 자연어 처리**

#### 의도 분류 (Intent Classification)
```python
intent = llm.classify_intent(
    user_input="너무 비싸",
    conversation_history=[...],
    current_product_info="나이키 운동화"
)
# Returns: {
#   "intent": "dissatisfied",
#   "confidence": 0.92,
#   "reason": "가격이 너무 비싸다",
#   "keywords": ["저렴한", "가성비"]
# }
```

#### 검색어 생성 (Query Generation)
```python
query = llm.generate_search_query(
    original_product_name="나이키 에어맥스",
    user_feedback="너무 비싸",
    extracted_keywords=["저렴한", "가성비"],
    conversation_history=[...]
)
# Returns: "운동화 저렴한 가성비"
```

### 3. `coupang_playwright_agent.py`
**상품 페이지 탐색 에이전트**

- 리뷰/문의 섹션 실시간 분석
- 키워드 기반 정보 추출
- 장바구니 추가 자동화

```python
agent = CoupangProductAgent(page)

# 질문에 답변
answer = await agent.answer_user_question("발볼 넓은 사람도 신을 수 있대?")

# 장바구니 추가
result = await agent.add_product_to_cart()
```

### 4. `coupang_search_agent.py`
**검색 기능 제공**

- 쿠팡 검색 자동화
- 검색 결과 파싱
- 상품 정보 추출

```python
search_agent = CoupangSearchAgent(page)
results = await search_agent.search("운동화 저렴한", max_results=5)
```

## 🎨 주요 특징

### 1. 강력한 안티봇 우회
```python
# JavaScript injection
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

# Akamai 쿠키 특별 처리
if name in ['_abck', 'bm_sz', 'bm_sv']:
    cookie_dict['secure'] = True
    cookie_dict['httpOnly'] = True
    cookie_dict['sameSite'] = 'None'
```

### 2. 자동 재시도 및 폴백
```python
# httpx → requests → curl 순서로 폴백
status, url, text = _try_httpx(candidates, headers, timeout)
if text is None:
    status, url, text = _try_requests(candidates, headers, timeout)
if text is None:
    status, url, text = _try_curl(candidates, headers, timeout)
```

### 3. 컨텍스트 기반 대화
```python
@dataclass
class ConversationState:
    current_url: Optional[str] = None
    current_product_name: Optional[str] = None
    search_results: List[SearchResult] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    waiting_for_clarification: bool = False
```

## 🐛 트러블슈팅

### 1. "This site can't be reached" 오류
- **원인**: Akamai 봇 방어 시스템
- **해결**: 최신 쿠키를 `cookie.txt`에 저장 후 재시도

### 2. Timeout 오류
- **원인**: 네트워크 지연 또는 페이지 로딩 시간 초과
- **해결**: `--timeout` 옵션으로 대기 시간 증가

### 3. 검색 결과 없음
- **원인**: 페이지 구조 변경 또는 셀렉터 불일치
- **해결**: 브라우저 보이게 실행하여 페이지 확인 (headless 플래그 제거)

## 📄 라이선스

This project is for educational purposes only.

## 👥 기여자

- Ellie - Initial work

## 📞 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 등록해주세요.
