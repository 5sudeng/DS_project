# Execution Flow Documentation (`junha_1` branch)

This document outlines the execution flow of the Coupang Shopping Assistant on the `junha_1` branch.
**Note**: This branch uses an LLM-driven intent mapping system (`map_command_to_actions`) instead of hardcoded state transitions.

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
    - Parses command-line arguments.
    - Initializes `ShoppingCLI`.
    - Calls `cli.run()`.

## 3. CLI Controller: `ShoppingCLI`
- **File**: `interface/cli/controller.py`
- **Class**: `ShoppingCLI` (inherits from `IOMixin`, `BrowserMixin`, `SearchMixin`, `IntentMixin`)
- **Action**:
    - **`run()`**:
        - Prints welcome message.
        - Initializes Playwright browser session (`bootstrap_browser`).
        - Initializes services.
        - Enters the conversation loop: `_conversation_loop()`.
    - **`_conversation_loop()`**:
        - Calls `_ask_ai_memory_preference()` to toggle AI memory.
        - Enters `while True` loop.
        - **Input**: Waits for user input via `input("삐\n > ")`.
        - **Handling**: Calls `_handle_user_input(user_input)`.

## 4. Intent & Action Mapping: `IntentMixin`
- **File**: `interface/cli/mixins/intent_mixin.py`
- **Method**: `_handle_user_input(user_input)`
- **Action**:
    1.  **Plan**: Calls `self.llm.map_command_to_actions(user_input)` to convert natural language into a structured plan (JSON).
    2.  **Execute**: Calls `_execute_actions(actions)` to run the planned actions.

## 5. Search Execution (Scenario: "search 온습도계")
- **User Input**: `"search 온습도계"` (or similar natural language)
- **LLM Mapping**: Maps to `{"action": "search_page", "query": "온습도계"}`.
- **Method**: `_execute_actions` -> `search_page` block.
- **Action**:
    - Calls `_search_only("온습도계")` in `SearchMixin`.
    - Calls `SearchService.search_page`.
    - Calls `_display_results` to print the list.

## 6. Product Selection (Scenario: "5")
- **User Input**: `"5"`
- **LLM Mapping**: Maps to `{"action": "select_result", "index": 5}`.
- **Method**: `_execute_actions` -> `select_result` block.
- **Action**:
    - Calls `_select_search_result(5)` in `SearchMixin`.
    - Calls `_load_product(url)` in `BrowserMixin`.
    - **BrowserMixin**:
        - Navigates to product page.
        - Collects data (`_collect_structured_data`).
        - Generates summary (`generate_product_summary`).

## 7. User Question (Scenario: "가격이 얼마야?")
- **User Input**: `"가격이 얼마야?"`
- **LLM Mapping**: Maps to `{"action": "question", "query": "가격이 얼마야?"}`.
- **Method**: `_execute_actions` -> `question` block.
- **Action**:
    - Calls `_handle_question("가격이 얼마야?")`.
    - Calls `BrowserService.answer_user_question`.

## 8. Add to Cart (Scenario: "장바구니에 담아줘")
- **User Input**: `"장바구니에 담아줘"`
- **LLM Mapping**: Maps to `{"action": "add_to_cart"}`.
- **Method**: `_execute_actions` -> `add_to_cart` block.
- **Action**:
    - Calls `_handle_add_to_cart`.
    - Calls `BrowserService.add_product_to_cart`.

## 9. Navigate to Cart (Scenario: "장바구니로 이동해줘")
- **User Input**: `"장바구니로 이동해줘"`
- **LLM Mapping**: Maps to `{"action": "navigate_to_cart"}`.
- **Method**: `_execute_actions` -> `navigate_to_cart` block.
- **Action**:
    - Calls `_handle_navigate_to_cart`.
    - Calls `BrowserService.navigate_to_cart`.
