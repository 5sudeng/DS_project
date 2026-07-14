프로젝트 작업 요약: AI 기반 쿠팡 쇼핑 어시스턴트
1. 프로젝트 개요
프로젝트명: AI 기반 쿠팡 쇼핑 어시스턴트 (AI-Powered Coupang Shopping Assistant) 목표: 자연어를 이해하고, 상품 페이지를 탐색하며, 질문에 답변(텍스트 및 이미지 활용)하고, 장바구니를 관리하는 대화형 CLI 에이전트 개발. 핵심 기술: Python, Playwright, OpenAI GPT-4o-mini (Text & Vision), LangChain.

2. 최근 주요 성과 (지난 ~2주)
🏗️ 아키텍처 리팩토링 및 정리
모듈화 설계: 단일 스크립트 형태였던 코드를 구조화된 아키텍처로 대대적으로 리팩토링했습니다:
interface/cli: CLI 로직을 ShoppingCLI 컨트롤러와 기능별 Mixin(BrowserMixin, SearchMixin, IntentMixin)으로 분리.
services: LLM, 브라우저, 검색 등 핵심 비즈니스 로직을 전용 서비스로 격리.
scrapers: 데이터 유형별(HTML, 리뷰, 문의, 수량, BTF)로 원자적(atomic) 스크레이퍼 구현.
레거시 제거: 구형 RAG 컴포넌트, 복잡한 크롤링 파이프라인, Clova OCR 연동 코드를 제거하고 간소화된 접근 방식으로 전환했습니다.
👁️ 멀티모달 RAG (Vision API)
이미지 이해: GPT-4o-mini Vision을 통합하여 상품 상세 정보를 "볼" 수 있게 되었습니다.
작동 방식:
상품 상세 이미지(Below-The-Fold) 다운로드.
이미지와 텍스트 청크 연결.
사용자 질문(예: "성분이 뭐야?")에 적합한 이미지를 동적으로 선택.
이미지를 LLM에 전송하여 근거 있는 답변 생성.
🛒 쇼핑 기능 강화
수량 포함 장바구니 담기: "이거 2개 담아줘"와 같이 특정 수량을 지정하여 장바구니에 담는 기능 구현.
상품 요약: 페이지 방문 즉시 CLI에 간결한 상품 요약을 생성하여 표시.
아티팩트 수집: 리뷰, 문의, OCR 데이터 등 에이전트의 지식을 뒷받침할 "아티팩트" 수집 기능 강화.
🔧 안정성 및 개선
OpenAI OCR: Clova OCR 의존성을 제거하고 OpenAI Vision API로 전환하여 통합성 및 성능 향상.
에러 처리: "Access Denied" 페이지 및 봇 탐지 상황에 대한 처리 로직 개선.
JSON-LD 파싱: DOM 파싱 실패 시 JSON-LD 스키마를 우선적으로 사용하여 데이터 추출 정확도 향상.
3. 코드 구조 요약
디렉토리	목적	주요 파일
interface/cli	사용자 인터랙션	controller.py, mixins/*.py
services	핵심 로직	llm_service.py, browser_service.py, search_service.py
scrapers	데이터 추출	html_fetcher.py, review_scraper.py, product_detail_scraper.py
processors	데이터 처리	ocr_processor.py, chunker.py
core	유틸리티	state.py, utils.py, settings.py
4. 주요 깃 히스토리 하이라이트
90084c1 (5일 전): CLI를 Controller/Mixin으로 분리하고 OCR/BTF 핸들러를 추가하는 대규모 리팩토링.
e1f6907 (6일 전): Clova 의존성을 제거하고 OpenAI OCR로 전환.
e83ec61 (5일 전): 수량 지원 장바구니 담기 기능 구현.
955fc3f (5일 전): JSON-LD를 활용한 데이터 추출 개선.
da5cdc5 (6일 전): 구형 RAG 및 크롤링 컴포넌트 대거 삭제 및 정리.
5. 현재 상태
프로젝트는 안정적이고 기능이 풍부한 상태입니다. 모듈식 아키텍처로의 전환이 완료되었으며, 에이전트는 고급 멀티모달 상호작용을 지원합니다. 문서(README.md) 또한 이러한 변경 사항을 반영하여 최신 상태로 업데이트되었습니다.