# 검색 결과 페이지네이션 기능 가이드

## 📋 개요

검색 결과를 **5개씩 한 페이지에 표시**하고, 사용자가 선호하는 상품이 없으면 같은 페이지 내 다음 5개를 제시하거나 다른 페이지로 이동할 수 있도록 구현했습니다.

---

## 🎯 주요 기능

### 1. **5개씩 상품 표시**
- 검색 결과는 항상 5개씩 페이지 단위로 표시됨
- 번호 1-5로 선택 가능

### 2. **현재 페이지 내 다음 상품 로드**
- 사용자가 "없음" 또는 "다음" 입력
- **같은 페이지에서 다음 5개 상품 로드**
- 현재 페이지에 5개 미만의 상품만 남으면 자동으로 감지

### 3. **페이지 소진 감지 및 페이지 이동**
- 현재 페이지에 5개 미만 또는 더 이상 상품이 없으면:
  - "페이지 X에는 더 이상 상품이 없습니다" 메시지 표시
  - 이동할 페이지 번호를 사용자에게 요청

### 4. **언제든 새로운 검색 가능**
- 검색 결과 보는 중 언제든지 "검색" 또는 "다른 상품" 입력
- 새로운 검색어 입력 가능

---

## 🔧 구현 상세

### 1. `ConversationState` (state.py) - 상태 관리

```python
# 새로 추가된 필드들
current_search_query: Optional[str] = None  # 현재 검색어
all_search_results: List["SearchResult"] = field(default_factory=list)  # 전체 결과 (향후 캐시용)
current_page: int = 1                       # 현재 페이지 (1부터 시작)
page_offset: int = 0                        # 현재 페이지 내 오프셋
results_per_page: int = 5                   # 항상 5개씩
```

**역할**: 검색 진행 상태, 현재 페이지, 오프셋 등을 추적

---

### 2. `CoupangSearchAgent` (coupang_search_agent.py) - 검색 에이전트

#### `search_page(query, page_num=1, max_results=5)` (신규)
```python
async def search_page(self, query: str, page_num: int = 1, max_results: int = 5) -> List[SearchResult]:
    """
    Search for products on a specific page of Coupang.
    
    Args:
        query: Search query string
        page_num: Page number (1-indexed)
        max_results: Maximum number of results to return per page
    
    Returns:
        List of SearchResult objects
    """
```

**동작**:
1. 초기 검색 수행 (page_num=1인 경우)
2. page_num > 1이면 `_navigate_to_page(page_num)` 호출하여 해당 페이지로 이동
3. 5개 상품 파싱 후 반환

#### `_navigate_to_page(page_num)` (신규)
```python
async def _navigate_to_page(self, page_num: int) -> None:
    """Navigate to a specific page in search results."""
```

**동작**:
1. 현재 URL에서 page 파라미터 추출
2. URL을 `?page=N` 형식으로 변환
3. Playwright로 새 페이지 로드

---

### 3. `InteractiveShoppingCLI` (interactive_shopping_cli.py) - CLI 로직

#### 입력 처리 개선 - `_handle_user_input()`

사용자 입력에 따른 처리:
```
- 1-5: 상품 번호 입력 → _select_search_result() → 상품 로드
- "없음"/"다음": 다음 5개 상품 또는 페이지 이동 → _show_next_items_in_page()
- "검색"/"다른 상품": 새 검색 시작 → _start_with_search()
```

#### `_show_next_items_in_page()` (신규) - 다음 상품 로드

```python
async def _show_next_items_in_page(self, user_input: str):
    """Show next 5 items in current page or handle pagination."""
    # 1. 페이지 오프셋 증가
    self.state.page_offset += self.state.results_per_page
    
    # 2. 다음 페이지 로드 시도
    next_results = await self.search_agent.search_page(
        self.state.current_search_query,
        page_num=self.state.current_page + 1,
        max_results=5
    )
    
    # 3. 결과 분석
    if len(next_results) >= 5:
        # 정상 페이지 (5개 이상)
        self.state.current_page += 1
        self.state.search_results = next_results
        await self._select_from_search_results()
    elif len(next_results) > 0 and len(next_results) < 5:
        # 마지막 페이지 (5개 미만)
        print(f"⚠️  페이지 {self.state.current_page + 1}에는 {len(next_results)}개의 상품만 남아있습니다.")
        await self._ask_page_navigation()
    else:
        # 더 이상 상품 없음
        print(f"😔 페이지 {self.state.current_page}에는 더 이상 상품이 없습니다.")
        await self._ask_page_navigation()
```

**흐름**:
1. 다음 페이지의 상품 로드 시도
2. 5개 이상이면: 페이지 증가 → 5개 상품 표시
3. 5개 미만이면: 나머지 상품 표시 → 페이지 이동 문의
4. 0개이면: "더 이상 상품 없음" → 페이지 이동 문의

#### `_ask_page_navigation()` (신규) - 페이지 이동 안내

```python
async def _ask_page_navigation(self):
    """Ask user which page to navigate to."""
    print(f"🔍 현재 페이지: {self.state.current_page}")
    user_response = input("📄 이동하고 싶은 페이지 번호를 입력하세요 (또는 '돌아가기'/'검색'): ").strip()
    
    if user_response.isdigit():
        page_num = int(user_response)
        self.state.current_page = page_num
        await self._load_current_page()
    elif user_response.lower() in ["검색", "search"]:
        await self._start_with_search()
    # ...
```

**사용자 입력 옵션**:
- 숫자: 해당 페이지로 이동
- "돌아가기"/"back": 이전 페이지로 이동
- "검색"/"search": 새로운 검색 시작

#### `_load_current_page()` (신규) - 현재 페이지 로드

```python
async def _load_current_page(self):
    """Load products for the current page."""
    print(f"⏳ 페이지 {self.state.current_page} 로드 중...")
    results = await self.search_agent.search_page(
        self.state.current_search_query,
        page_num=self.state.current_page,
        max_results=5
    )
    
    if results:
        self.state.search_results = results
        await self._select_from_search_results()
    else:
        print(f"😔 페이지 {self.state.current_page}에 상품이 없습니다.")
        await self._ask_page_navigation()
```

**역할**: 사용자가 지정한 페이지의 상품 로드

---

## 💬 사용자 인터랙션 예시

### 시나리오: 검색 후 페이지 탐색

```
📦 상품 URL을 입력하세요 (또는 'search'로 검색 시작): search
🔍 검색어를 입력하세요: 가성비 좋은 운동화

🔍 검색 중: '가성비 좋은 운동화'
✓ 5개 상품 발견

📦 검색 결과:

1. 아디다스 러닝화 - 가성비
   가격: 52,000원
   평점: 4.7

2. 언더아머 농구화
   가격: 68,000원
   평점: 4.5

3. 뉴발란스 운동화
   가격: 75,000원
   평점: 4.6

4. 리복 클래식화
   가격: 45,900원
   평점: 4.4

5. 푸마 스포츠화
   가격: 55,000원
   평점: 4.3

🔢 원하는 상품의 번호를 입력하세요 (1-5) 또는 '없음'/'다음'으로 다음 상품 확인, '검색'으로 새 검색:

💬 > 없음

⏳ 페이지 2 로드 중...
🔍 검색 중: '가성비 좋은 운동화' (페이지 2)
✓ 5개 상품 발견

📦 검색 결과:

1. 조던 농구화
   가격: 120,000원
   평점: 4.8

2. 나이키 에어맥스
   가격: 95,000원
   평점: 4.7

3. 컨버스 올스타
   가격: 42,000원
   평점: 4.5

4. 반스 스니커
   가격: 38,500원
   평점: 4.4

5. 뉴발란스 574
   가격: 72,000원
   평점: 4.6

🔢 원하는 상품의 번호를 입력하세요 (1-5) 또는 '없음'/'다음'으로 다음 상품 확인, '검색'으로 새 검색:

💬 > 2

✓ 선택: 나이키 에어맥스

⏳ 상품 페이지를 불러오는 중...
✓ 상품: 나이키 에어맥스
   URL: https://www.coupang.com/vp/products/...

❓ 무엇이 궁금하신가요?

💬 > 가격이 좀 비싼 것 같아

[의도 파악: dissatisfied (신뢰도: 0.92)]
🔍 이해했습니다: 가격이 비싼 편입니다
새로운 상품을 찾아보겠습니다...
💡 검색어: '운동화 저렴한 가성비'

🔍 검색 중: '운동화 저렴한 가성비'
✓ 5개 상품 발견

📦 검색 결과: (새로운 검색)
...
```

---

### 시나리오: 마지막 페이지 도달

```
💬 > 없음

⏳ 페이지 5 로드 중...
🔍 검색 중: '가성비 좋은 운동화' (페이지 5)
✓ 2개 상품 발견

📦 검색 결과:

1. 크록스 샌들
   가격: 28,000원
   평점: 4.2

2. 지클래식 슬리퍼
   가격: 22,000원
   평점: 4.0

⚠️  페이지 5에는 2개의 상품만 남아있습니다.

🔍 현재 페이지: 5
📄 이동하고 싶은 페이지 번호를 입력하세요 (또는 '돌아가기'/'검색'):

💬 > 검색

🔍 검색어를 입력하세요: 겨울 부츠
```

---

## 📊 상태 흐름도

```
초기 상태
    ↓
사용자 검색 입력
    ↓
_start_with_search()
    ├─ query 입력
    ├─ _perform_search(query)
    │  ├─ current_search_query = query
    │  ├─ current_page = 1
    │  ├─ page_offset = 0
    │  └─ search_results = [5개]
    └─ _select_from_search_results() 호출
         ↓ (사용자 입력 대기)
         ├─ 1-5: _select_search_result() → 상품 로드
         ├─ "없음"/"다음": _show_next_items_in_page()
         │  ├─ page_offset += 5
         │  ├─ search_page(query, page_num=2) 호출
         │  ├─ 결과 분석
         │  │  ├─ 5개 이상: current_page += 1, search_results = [5개], 다시 표시
         │  │  ├─ 1~4개: 나머지 표시, _ask_page_navigation()
         │  │  └─ 0개: "더 이상 상품 없음", _ask_page_navigation()
         │  └─ _ask_page_navigation() 호출
         │     ├─ 숫자 입력: current_page = N, _load_current_page()
         │     ├─ "돌아가기": current_page -= 1, _load_current_page()
         │     └─ "검색": _start_with_search() 호출
         └─ "검색"/"다른 상품": _start_with_search() 호출
```

---

## 🎮 사용 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `1-5` | 상품 선택 | `2` → 2번 상품 로드 |
| `없음` | 다음 상품 또는 페이지 이동 | `없음` → 다음 5개 로드 |
| `다음` | 위와 동일 | `다음` → 다음 5개 로드 |
| `검색` | 새로운 검색 시작 | `검색` → 새 검색어 입력 |
| `다른 상품` | 새로운 검색 시작 | `다른 상품` → 새 검색어 입력 |
| 페이지 번호 | 해당 페이지로 이동 | `3` → 3번 페이지 로드 |
| `돌아가기` | 이전 페이지로 이동 | `돌아가기` → 이전 페이지 로드 |

---

## 🔑 주요 특징

### ✅ 구현됨
1. **5개씩 페이지네이션**: 항상 5개 상품 단위
2. **현재 페이지 내 탐색**: "없음"으로 같은 페이지 내 다음 5개 로드
3. **페이지 소진 감지**: 5개 미만 또는 0개 자동 감지
4. **페이지 이동**: 숫자 입력으로 특정 페이지 이동
5. **언제든 새 검색 가능**: "검색" 명령으로 언제든 새로운 검색 시작
6. **상태 추적**: current_page, page_offset으로 정확한 위치 관리

### 📝 참고사항
1. **페이지 번호 1부터 시작**: 사용자 입력 1 = 첫 번째 페이지
2. **URL 기반 이동**: `?page=N` 파라미터로 페이지 이동
3. **상품 단위 제목**: 각 페이지의 상품은 1-5로 번호 매김

---

## 🚀 실행 방법

```bash
python -m agent.interactive_shopping_cli --cookie-file cookie.txt
```

기존과 동일하게 실행됩니다. 추가로 "없음", "다음", "검색", "페이지 번호" 명령을 사용할 수 있습니다.
