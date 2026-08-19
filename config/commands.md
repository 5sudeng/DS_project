# 쇼핑 어시스턴트 명령어 레퍼런스

이 문서는 AI 쇼핑 어시스턴트가 사용자의 자연어 입력을 처리할 때 사용할 수 있는 모든 명령(actions)을 정리한 것입니다.

## 명령어 카테고리

### 1. Navigation (탐색)

#### `open_url`
특정 URL 또는 사이트로 이동합니다.

**파라미터:**
- `url` (string, required): 이동할 URL

**예시:**
```json
{"action": "open_url", "url": "https://www.coupang.com/"}
```

**사용 예:**
- "쿠팡 열어줘" → `[{"action": "open_url", "url": "https://www.coupang.com/"}]`
- "네이버 쇼핑 가줘" → `[{"action": "open_url", "url": "https://shopping.naver.com/"}]`

---

#### `navigate_to_cart`
장바구니 페이지로 이동합니다.

**파라미터:** 없음

**예시:**
```json
{"action": "navigate_to_cart"}
```

**사용 예:**
- "장바구니 보여줘" → `[{"action": "navigate_to_cart"}]`
- "장바구니 확인" → `[{"action": "navigate_to_cart"}]`

---

### 2. Search (검색)

#### `search_page`
쿠팡에서 상품을 검색합니다.

**파라미터:**
- `query` (string, required): 검색어

**예시:**
```json
{"action": "search_page", "query": "헤드셋"}
```

**사용 예:**
- "헤드셋 찾아줘" → `[{"action": "search_page", "query": "헤드셋"}]`
- "무선 키보드 검색" → `[{"action": "search_page", "query": "무선 키보드"}]`

---

#### `apply_sort`
검색 결과에 정렬 옵션을 적용합니다.

**파라미터:**
- `sort_type` 또는 `option` (string, required): 정렬 방식
  - `"낮은가격순"`: 가격이 낮은 순서
  - `"높은가격순"`: 가격이 높은 순서
  - `"판매량순"`: 판매량이 많은 순서
  - `"랭킹순"`: 랭킹 순서
  - `"최신순"`: 최신 상품 순서
  - `"평점순"`: 평점이 높은 순서

**예시:**
```json
{"action": "apply_sort", "sort_type": "판매량순"}
```

**사용 예:**
- "판매량 많은 순으로" → `[{"action": "apply_sort", "sort_type": "판매량순"}]`
- "최저가부터" → `[{"action": "apply_sort", "sort_type": "낮은가격순"}]`

---

#### `apply_shipping`
배송비 필터를 적용합니다.

**파라미터:**
- `shipping_option` 또는 `option` (string, required): 배송비 옵션
  - `"배송비포함"`: 배송비 포함 가격으로 표시
  - `"배송비제외"`: 배송비 제외 가격으로 표시

**예시:**
```json
{"action": "apply_shipping", "shipping_option": "배송비포함"}
```

**사용 예:**
- "배송비 포함해서 보여줘" → `[{"action": "apply_shipping", "shipping_option": "배송비포함"}]`

---

#### `related_keywords`
현재 검색어와 연관된 검색어 목록을 표시합니다.

**파라미터:** 없음

**예시:**
```json
{"action": "related_keywords"}
```

**사용 예:**
- "비슷한 검색어 보여줘" → `[{"action": "related_keywords"}]`
- "연관 검색어" → `[{"action": "related_keywords"}]`

---

### 3. Product (상품)

#### `load_product`
특정 상품 페이지를 로드합니다.

**파라미터:**
- `url_or_index` (string|int, required): 상품 URL 또는 검색 결과 인덱스

**예시:**
```json
{"action": "load_product", "url_or_index": 3}
{"action": "load_product", "url_or_index": "https://www.coupang.com/vp/products/..."}
```

**사용 예:**
- "3번째 상품 보여줘" → `[{"action": "load_product", "url_or_index": 3}]`
- "첫번째 거 열어줘" → `[{"action": "load_product", "url_or_index": 1}]`

**참고:**
- 상품 로드 시 자동으로 상품 정보(리뷰, Q&A, 상세정보 등)가 수집됩니다.

---

#### `select_result`
검색 결과에서 특정 번호를 선택합니다 (load_product와 유사).

**파라미터:**
- `index` (int, required): 선택할 상품 번호

**예시:**
```json
{"action": "select_result", "index": 2}
```

**사용 예:**
- "2번 선택" → `[{"action": "select_result", "index": 2}]`

---

#### `question`
현재 로드된 상품에 대해 질문합니다.

**파라미터:**
- `query` (string, required): 질문 내용

**예시:**
```json
{"action": "question", "query": "이 상품의 칼로리가 얼마니?"}
```

**사용 예:**
- "성분 알려줘" → `[{"action": "question", "query": "성분이 뭐야?"}]`
- "칼로리가 궁금해" → `[{"action": "question", "query": "칼로리가 얼마야?"}]`

---

#### `add_to_cart`
현재 상품을 장바구니에 담습니다.

**파라미터:**
- `quantity` (int, optional, default=1): 수량

**예시:**
```json
{"action": "add_to_cart", "quantity": 2}
```

**사용 예:**
- "장바구니에 넣어줘" → `[{"action": "add_to_cart", "quantity": 1}]`
- "2개 담아줘" → `[{"action": "add_to_cart", "quantity": 2}]`

---

### 4. Display (표시)

#### `read_results`
검색 결과의 상위 N개를 읽어줍니다.

**파라미터:**
- `top_n` (int, optional, default=3): 읽을 상품 개수

**예시:**
```json
{"action": "read_results", "top_n": 5}
```

**사용 예:**
- "상위 3개 보여줘" → `[{"action": "read_results", "top_n": 3}]`
- "결과 읽어줘" → `[{"action": "read_results", "top_n": 3}]`

---

#### `summarize`
검색 결과 또는 현재 상품을 요약/추천합니다.

**파라미터:**
- `top_n` (int, optional, default=3): 요약할 상품 개수 (검색 결과 요약 시)

**예시:**
```json
{"action": "summarize", "top_n": 3}
```

**사용 예:**
- "추천해줘" → `[{"action": "summarize", "top_n": 3}]`
- "요약해줘" → `[{"action": "summarize"}]`

**참고:**
- 검색 결과 페이지에서 사용 시: 상위 N개 상품 요약
- 상품 페이지에서 사용 시: 현재 상품 요약

---

### 5. System (시스템)

#### `exit`
쇼핑 세션을 종료합니다.

**파라미터:** 없음

**예시:**
```json
{"action": "exit"}
```

**사용 예:**
- "종료" → `[{"action": "exit"}]`
- "그만" → `[{"action": "exit"}]`

---

## 복합 명령 예시

여러 명령을 순서대로 실행하는 복합 명령 예시입니다.

### 예시 1: 검색 + 정렬 + 읽기
**입력:** "사람들이 많이 산 좋은 헤드셋 사고싶어"

**출력:**
```json
{
  "actions": [
    {"action": "search_page", "query": "헤드셋"},
    {"action": "apply_sort", "sort_type": "판매량순"},
    {"action": "read_results", "top_n": 3}
  ]
}
```

---

### 예시 2: 상품 로드 + 요약
**입력:** "3번째 거 아이템을 사고싶어"

**출력:**
```json
{
  "actions": [
    {"action": "load_product", "url_or_index": 3},
    {"action": "summarize"}
  ]
}
```

**참고:** `load_product`를 실행하면 자동으로 상품 정보가 수집되므로, `summarize`가 수집된 정보를 바탕으로 요약을 생성합니다.

---

### 예시 3: 질문 + 장바구니 추가
**입력:** "칼로리 알려주고 괜찮으면 장바구니에 넣어줘"

**출력:**
```json
{
  "actions": [
    {"action": "question", "query": "칼로리가 얼마야?"}
  ]
}
```

**참고:** "괜찮으면"과 같은 조건부 동작은 사용자의 다음 입력을 기다립니다.

---

### 예시 4: 검색 + 정렬 + 요약 + 정렬 변경
**입력:** "검은색 모자를 추천해주고 별점순으로 보여줘"

**출력:**
```json
{
  "actions": [
    {"action": "search_page", "query": "검은색 모자"},
    {"action": "summarize", "top_n": 3},
    {"action": "apply_sort", "sort_type": "평점순"},
    {"action": "read_results", "top_n": 3}
  ]
}
```

---

## 명령 실행 순서

명령은 배열 순서대로 실행됩니다. 각 명령은 이전 명령의 결과를 기반으로 실행될 수 있습니다.

예를 들어:
1. `search_page` → 검색 결과 저장
2. `apply_sort` → 저장된 검색 결과에 정렬 적용
3. `read_results` → 정렬된 결과 표시

---

## 주의사항

1. **상태 의존성**: 일부 명령은 특정 상태에서만 유효합니다.
   - `apply_sort`, `apply_shipping`: 검색 결과가 있어야 함
   - `question`, `add_to_cart`: 상품 페이지가 로드되어 있어야 함

2. **자동 수집**: `load_product` 실행 시 자동으로 상품 정보(리뷰, Q&A, 상세정보)가 백그라운드에서 수집됩니다.

3. **조건부 실행**: 사용자의 조건부 요청("~하면", "괜찮으면")은 단일 명령으로 처리하고, 조건 평가 후 사용자의 다음 입력을 기다립니다.
