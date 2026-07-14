상세 프로젝트 개발 이력 및 기술 분석 보고서
이 문서는 프로젝트의 시작부터 현재까지의 개발 과정을 기술적 의사결정, 아키텍처 변화, 핵심 로직 구현 관점에서 심층적으로 분석한 보고서입니다.

1. 태동기: 데이터 수집 및 기본 크롤링 (2025년 10월 초 ~ 중순)
목표: 쿠팡 상품 페이지에서 정형/비정형 데이터를 수집하여 분석 가능한 형태로 저장.

1.1. 원자적 스크레이퍼(Atomic Scrapers) 구현
초기 개발은 단일 기능을 수행하는 독립적인 스크립트 형태로 시작되었습니다.

fetch_html.py: requests 라이브러리를 사용하여 HTML을 가져오는 기본 모듈. 초기에는 단순한 User-Agent 헤더만 사용했으나, 차단 문제로 인해 추후 curl_cffi와 같은 고도화된 라이브러리로 대체되는 기반이 되었습니다.
review.py & inquiries.py:
도전 과제: 리뷰와 문의 내역은 페이지네이션이 적용되어 있고 동적으로 로딩됨.
해결: 네트워크 트래픽 분석을 통해 숨겨진 API 엔드포인트를 찾아내어, 브라우저 렌더링 없이 JSON 데이터를 직접 수집하는 방식으로 속도를 최적화했습니다.
quantity.py: 재고 수량 파악을 위한 로직. 장바구니 담기 시도 시 반환되는 응답을 분석하여 최대 구매 가능 수량을 역추적하는 로직이 포함되었습니다.
1.2. 데이터 파이프라인 오케스트레이션
crawling/main.py: 개별 스크립트들을 엮어 하나의 워크플로우로 통합.
Category URL -> Product List -> Detail Page -> Reviews/Inquiries 순서로 이어지는 순차적 실행 흐름을 제어.
CSV 스키마 설계: products.csv에 itemId, vendorItemId 등 쿠팡 내부 식별자를 포함하여 데이터 무결성을 보장했습니다.
2. 성장기: RAG 시스템 및 데이터 가공 (2025년 10월 말)
목표: 수집된 방대한 텍스트 데이터를 LLM이 이해하고 검색할 수 있는 형태로 가공 (Retrieval-Augmented Generation).

2.1. 데이터 전처리 및 청킹 (Chunking)
processors/chunker.py
:
로직: 단순히 길이로 자르는 것이 아니라, 문맥 유지를 위해 의미 단위(문단, 섹션)로 텍스트를 분할.
메타데이터: 각 청크에 원본 상품 ID, 섹션 제목 등을 메타데이터로 태깅하여 검색 정확도를 높였습니다.
to_schema.py: 비정형 HTML 데이터를 LLM 학습/검색에 용이한 JSONL(JSON Lines) 포맷으로 정규화.
2.2. 벡터 검색 인프라 구축
FAISS 도입: 로컬 환경에서의 빠른 유사도 검색을 위해 Facebook AI Similarity Search(FAISS) 라이브러리 도입.
rag_with_detail.py:
사용자 질문(Query)을 임베딩 -> FAISS 인덱스 검색 -> 상위 k개 청크 추출 -> LLM 프롬프트에 주입(Context Injection)하는 RAG의 표준 흐름을 구현했습니다.
2.3. 멀티모달 데이터 확보 (BTF & OCR)
BTF (Below-The-Fold) 수집: 상품 상세 페이지 하단의 긴 이미지(상세 설명)를 다운로드하는 btf.py 구현.
OCR 통합: 이미지 내 텍스트 정보를 검색 가능하게 만들기 위해 OCR 도입. 초기에는 Clova OCR API를 사용했으나, 비용 및 통합 편의성을 위해 추후 OpenAI Vision으로 전환되었습니다.
3. 도약기: 대화형 에이전트 아키텍처 (2025년 11월)
목표: 정적인 데이터 검색을 넘어, 사용자와 대화하며 행동(Action)하는 AI 에이전트 개발.

3.1. CLI 컨트롤러 및 Mixin 패턴 (Architectural Refactoring)
단일 스크립트(main.py)의 비대화를 해결하기 위해 관심사 분리(Separation of Concerns) 원칙을 적용했습니다.

interface/cli/controller.py
 (ShoppingCLI):
애플리케이션의 상태(State)와 제어 흐름을 담당하는 중앙 컨트롤러.
Mixin을 통한 기능 모듈화:
BrowserMixin: Playwright 인스턴스 관리, 페이지 이동, 스크롤, 클릭 등 브라우저 조작 로직 캡슐화.
SearchMixin: 검색어 입력, 결과 파싱, 상품 선택 등 검색 관련 비즈니스 로직.
IntentMixin: 사용자 발화에서 의도(Intent)를 분류하고, 적절한 핸들러로 라우팅하는 로직.
3.2. 서비스 계층 (Service Layer) 도입
services/llm_service.py
: OpenAI API 호출 로직을 전담. 프롬프트 템플릿 관리 및 응답 파싱(JSON 모드 활용)을 담당.
services/browser_service.py
: BrowserMixin이 사용하는 하위 레벨의 브라우저 조작 기능을 제공하며, 재사용성을 높임.
3.3. 고급 쇼핑 기능 구현
장바구니 로직 (navigate_to_cart): 단순 페이지 이동뿐만 아니라, 현재 보고 있는 상품의 옵션을 선택하고 수량을 지정하여 장바구니에 담는 복합적인 액션 시퀀스 구현.
JSON-LD 활용: HTML 구조 변경에 취약한 CSS Selector 방식의 한계를 극복하기 위해, 페이지 내 삽입된 JSON-LD(구조화된 데이터)를 우선 파싱하고 실패 시 DOM 탐색으로 넘어가는 하이브리드 추출 전략 채택.
4. 성숙기: 멀티모달 완성 및 UX 고도화 (2025년 11월 말 ~ 현재)
목표: 시각(Vision)과 청각(Voice)을 아우르는 진정한 멀티모달 경험 제공 및 개인화.

4.1. Vision API 기반 멀티모달 RAG
동적 이미지 매핑:
텍스트 청크와 관련된 이미지 경로를 image_manifest로 관리.
질문이 들어오면 관련 텍스트 청크를 찾고, 그 청크에 연결된 이미지를 즉시 로드하여 GPT-4o Vision에 전송.
효과: "이 과자 영양성분표 보여줘"와 같은 질문에 대해, OCR 텍스트에 의존하지 않고 이미지를 직접 보고 답변하는 높은 정확도 달성.
4.2. 음성 인터페이스 (Voice IO) 및 개인화
core/voice_io.py
:
STT (Speech-to-Text): 마이크 입력을 실시간으로 녹음하여 텍스트로 변환.
TTS (Text-to-Speech): 에이전트의 응답을 음성으로 출력하여 핸즈프리 경험 제공.
메모리 시스템 (memory.txt, identity.txt):
사용자의 쇼핑 취향(선호 카테고리, 가격대 등)을 로컬 파일에 영구 저장.
대화가 시작될 때 이 정보를 로드하여 "지난번에 찾으시던 운동화 신상품이 나왔어요"와 같은 개인화된 발화 가능.
4.3. 안정성 및 성능 최적화
curl_cffi 도입: 일반적인 requests가 차단되는 문제를 해결하기 위해, 브라우저(Chrome)의 TLS 지문(Fingerprint)을 모방하는 curl_cffi 라이브러리 도입.
에러 핸들링 강화: "Access Denied" 페이지 감지 시 자동으로 쿠키를 갱신하거나 사용자에게 알림을 주는 회복 탄력성(Resilience) 확보.
5. 결론 및 향후 전망
이 프로젝트는 데이터 수집기(Crawler) -> 지식 검색 시스템(RAG) -> 행동하는 에이전트(Agent) -> **멀티모달 비서(Multimodal Assistant)**로 단계적으로 진화했습니다. 현재 아키텍처는 확장성이 뛰어나며(Mixin 패턴), 시각/청각 정보를 모두 활용할 수 있는 강력한 기반을 갖추고 있습니다. 향후에는 결제 자동화나 더욱 정교한 개인화 추천 알고리즘 도입이 가능한 상태입니다.