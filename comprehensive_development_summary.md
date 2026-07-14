프로젝트 개발 이력 및 기능 구현 요약
이 문서는 프로젝트 초기부터 현재까지의 코드 변경 사항(git log)을 분석하여, 단순한 커밋 메시지 나열이 아닌 실제 구현된 기능과 개발 흐름을 중심으로 정리한 보고서입니다.

1. 초기 데이터 수집 및 파이프라인 구축 (2025년 10월 초 ~ 중순)
핵심 활동: 쿠팡 상품 데이터 수집을 위한 기본 크롤링 모듈 구현 및 데이터셋 구축.

개별 스크레이퍼 구현:
fetch_html.py: 상품 페이지 HTML 다운로드.
review.py, inquiries.py, quantity.py: 리뷰, 문의, 재고 수량 등 특정 데이터 추출을 위한 전용 스크레이퍼 개발.
코드 특징: 초기에는 각 기능이 독립적인 스크립트로 존재했으며, 이후 crawling/ 디렉토리로 구조화됨.
데이터 파이프라인:
crawling/main.py: 카테고리 URL 수집부터 상세 정보 추출까지 이어지는 파이프라인 오케스트레이션 구현.
products.csv: 수집된 상품 정보를 관리하기 위한 CSV 스키마 정의 및 데이터 생성.
2. RAG (검색 증강 생성) 및 데이터 처리 고도화 (2025년 10월 말)
핵심 활동: 수집된 데이터를 LLM이 활용할 수 있도록 가공하고 벡터 검색(RAG) 시스템 구축.

데이터 청킹 및 구조화:
processors/chunker.py
: 텍스트 데이터를 의미 단위로 분할(Chunking)하는 로직 구현.
to_schema.py: 원시 데이터를 구조화된 JSON 포맷으로 변환.
벡터 저장소 구축:
rag/ 디렉토리 생성: FAISS를 활용한 벡터 인덱스(index.faiss) 생성 및 관리.
rag_with_detail.py: 상세 정보를 포함한 RAG 검색 로직 구현.
멀티모달 기초 마련:
btf.py (Below-The-Fold): 상품 상세 설명 이미지 다운로드 기능 추가.
ocr.py: 이미지 내 텍스트 추출을 위한 OCR 처리 모듈 추가 (초기 Clova OCR 도입).
3. 대화형 에이전트 및 CLI 아키텍처 수립 (2025년 11월)
핵심 활동: 사용자와 상호작용하는 CLI 에이전트 개발 및 모듈화된 아키텍처로의 리팩토링.

CLI 컨트롤러 및 Mixin 패턴 도입:
interface/cli/controller.py
: 중앙 제어 로직 구현.
mixins/: 기능을 세분화하여 모듈성 강화.
BrowserMixin: Playwright 브라우저 제어.
SearchMixin: 상품 검색 및 결과 처리.
IntentMixin: 사용자 의도(검색, 질문, 장바구니 등) 파악.
서비스 계층 분리:
services/llm_service.py
: LLM 호출 로직 캡슐화.
services/browser_service.py
: 브라우저 자동화 로직 고도화.
기능 확장:
장바구니 기능: "장바구니에 담아줘" 등의 명령을 처리하기 위한 로직 (navigate_to_cart intent) 추가.
JSON-LD 활용: DOM 파싱 실패 시 JSON-LD 스키마를 폴백으로 사용하여 데이터 추출 안정성 확보.
4. 멀티모달 통합 및 사용자 경험 개선 (2025년 11월 말 ~ 12월 초)
핵심 활동: 시각 정보(이미지) 활용 능력 강화 및 음성 인터페이스(Voice IO) 통합.

Vision API 통합:
image_manifest: 상품 이미지와 텍스트 청크를 매핑하여 질문에 맞는 이미지를 동적으로 탐색.
ocr_processor.py: OpenAI Vision API로 전환하여 OCR 및 이미지 분석 성능 향상.
음성 인터페이스 (Voice IO):
core/voice_io.py
: 음성 입력(STT) 및 출력(TTS) 모듈 구현.
io_mixin.py: CLI와 음성 입출력 연동.
개인화 및 메모리: memory.txt, identity.txt를 도입하여 사용자 선호도(카테고리 등)를 기억하고 반영.
사용자 피드백 강화:
검색 결과 요약 및 음성 안내 기능 추가.
브라우저 뷰포트 및 상호작용 개선.
5. 최신 최적화 및 안정화 (현재)
핵심 활동: 코드 정리, 성능 최적화, 에러 처리 강화.

레거시 제거: 초기 크롤링 파이프라인 및 구형 RAG 코드 제거, scrapers/ 및 services/ 중심의 깔끔한 구조로 재편.
에러 핸들링: curl_cffi 등을 활용한 봇 탐지 우회 및 "Access Denied" 처리 로직 강화.
출력 표준화: console_print 등을 통해 CLI 및 음성 출력 메시지를 일관성 있게 다듬음.
요약: 단순한 스크립트 형태의 크롤러로 시작하여, RAG 기반의 지식 검색, Playwright를 이용한 실시간 브라우저 제어, 그리고 Vision API와 음성 인터페이스를 갖춘 멀티모달 AI 에이전트로 진화해왔습니다. 최근에는 코드의 모듈화(Mixin 패턴)와 사용자 개인화(Memory)에 집중하고 있습니다.