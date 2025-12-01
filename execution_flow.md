# Execution Flow Documentation

This document outlines the execution flow of the Coupang Shopping Assistant, specifically focusing on the "Search" functionality.

## 1. Entry Point: `run_agent.sh`
- **File**: `run_agent.sh`
- **Role**: Wrapper script to set up the environment.
- **Action**:
    - Checks if the specific python executable exists in the conda environment.
    - Executes `main.py` using that python executable.

## 2. Main Application: `main.py`
- **File**: `main.py`
- **Role**: Application entry point.
- **Action**:
    - Parses command-line arguments (e.g., `--headless`, `--cookie-file`).
    - Initializes `ShoppingCLI`.
    - Calls `cli.run()`.

## 3. CLI Controller: `ShoppingCLI`
- **File**: `interface/cli/controller.py`
- **Class**: `ShoppingCLI` (inherits from `BrowserMixin`, `SearchMixin`, `IntentMixin`)
- **Action**:
    - **`run()`**:
        - Prints welcome message.
        - Initializes Playwright browser session (`bootstrap_browser`).
        - Initializes services: `BrowserService` (product agent) and `SearchService` (search agent).
        - Enters the conversation loop: `_conversation_loop()`.
    - **`_conversation_loop()`**:
        - Calls `_get_initial_product()` to start the interaction.

## 4. Initial Input Handling: `BrowserMixin`
- **File**: `interface/cli/mixins/browser_mixin.py`
- **Method**: `_get_initial_product()`
- **Action**:
    - Prompts user: `📦 상품 URL을 입력하세요 (또는 'search'로 검색 시작):`
    - **User Input**: `"search"`
    - Detects "search" keyword and calls `self._start_with_search()`.

## 5. Search Initiation: `SearchMixin`
- **File**: `interface/cli/mixins/search_mixin.py`
- **Method**: `_start_with_search()`
- **Action**:
    - Prompts user: `🔍 검색어를 입력하세요:`
    - **User Input**: `"온습도계"`
    - Calls `self._perform_search("온습도계")`.

## 6. Search Execution: `SearchService`
- **File**: `services/search_service.py`
- **Method**: `search(query="온습도계", max_results=5)`
- **Action**:
    1.  **Navigation**: Checks if on Coupang main page; if not, navigates to `https://www.coupang.com`.
    2.  **Input**: Finds the search bar (`_find_search_input`), clears it, and types "온습도계".
    3.  **Submit**: Presses "Enter" to submit the search.
    4.  **Wait**: Waits for results to load (`wait_for_load_state`).
    5.  **Parse**: Calls `_parse_search_results` to extract product data (title, price, url, etc.) from the DOM.
    6.  **Return**: Returns a list of `SearchResult` objects.

## 7. Result Display: `SearchMixin`
- **File**: `interface/cli/mixins/search_mixin.py`
- **Method**: `_select_from_search_results()`
- **Action**:
    - Formats the `SearchResult` list into a readable string.
    - Prints the results to the console.
    - Prompts user: `🔢 원하는 상품의 번호를 입력하세요 (1-5):`

## 8. Product Selection: `SearchMixin` & `BrowserMixin`
- **File**: `interface/cli/mixins/search_mixin.py`
- **Method**: `_select_search_result(selection=5)`
- **Action**:
    - **User Input**: `"5"`
    - Identifies the selected product from `self.state.search_results`.
    - Calls `self._load_product(selected.url)`.
- **File**: `interface/cli/mixins/browser_mixin.py`
- **Method**: `_load_product` -> `load_product_workflow`
- **Action**:
    1.  **Navigate**: `_navigate_to_product` loads the product page.
    2.  **Collect**: `_collect_product_data` extracts HTML, reviews, etc.
    3.  **Summary**: `_generate_product_summary` creates a summary using LLM.
    - Prompts user: `❓ 무엇이 궁금하신가요? (상품에 대해 질문해 주세요!)`

## 9. User Question (Price): `IntentMixin` & `BrowserService`
- **File**: `interface/cli/mixins/intent_mixin.py`
- **Method**: `_handle_user_input`
- **Action**:
    - **User Input**: `"가격이 얼마야?"`
    - **Intent Classification**: LLM classifies as `"question"`.
    - Calls `_handle_question("가격이 얼마야?")`.
- **File**: `services/browser_service.py`
- **Method**: `answer_user_question`
- **Action**:
    - Uses RAG (Retrieval Augmented Generation) or direct context to answer.
    - Returns answer (e.g., "이 상품의 가격은 165,000원입니다.").
    - Prints answer to console.

## 10. Add to Cart: `IntentMixin` & `BrowserService`
- **File**: `interface/cli/mixins/intent_mixin.py`
- **Method**: `_handle_user_input`
- **Action**:
    - **User Input**: `"장바구니에 담아줘"`
    - **Intent Classification**: LLM classifies as `"add_to_cart"`.
    - Calls `_handle_add_to_cart`.
- **File**: `services/browser_service.py`
- **Method**: `add_product_to_cart`
- **Action**:
    - Locates "Add to Cart" button on the page.
    - Clicks the button.
    - Verifies success (e.g., checks for confirmation modal or message).
    - Returns success message.

## 11. Navigate to Cart: `IntentMixin` & `BrowserService`
- **File**: `interface/cli/mixins/intent_mixin.py`
- **Method**: `_handle_user_input`
- **Action**:
    - **User Input**: `"장바구니로 이동해줘"`
    - **Intent Classification**: LLM classifies as `"navigate_to_cart"`.
    - Calls `_handle_navigate_to_cart`.
- **File**: `services/browser_service.py`
- **Method**: `navigate_to_cart`
- **Action**:
    - Navigates to `https://cart.coupang.com` (or clicks cart icon).
    - Returns confirmation message.
