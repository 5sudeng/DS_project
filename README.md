# 🛍️ AI-Powered Coupang Shopping Assistant

This project provides a large language model (LLM)-based interactive shopping assistant for Coupang. It integrates Playwright-based product-page exploration with intent classification, search‑query generation, and multi‑turn conversational navigation.

## Table of Contents
- Overview of Features
- Project Structure
- Installation
- Usage
- Example Interaction Flow
- Korean Examples (Intent Classification & Search Query Generation)
- Technology Stack
- Module Descriptions
- Troubleshooting
- License

## Overview of Features

### 1. Intent Classification (LLM-Based)
- Identifies the user’s intent such as: product inquiry, dissatisfaction, preference expression, or request for alternatives.
- Extracts rationale and important keywords to be used for next-step decisions.

### 2. Real-Time Product Exploration
- Loads Coupang product pages using Playwright.
- Extracts reviews, Q&A content, summary information, and key metadata.
- Produces grounded answers based strictly on the retrieved page content.

### 3. Dynamic Search and Recommendation
- When dissatisfaction is detected, the assistant automatically generates new search queries.
- Searches Coupang using refined terms and ranks search results.

### 4. Multi‑Turn Conversational Interface
- Maintains conversation history across steps.
- Supports iterative refinement of user preferences.
- Allows optional automated cart addition.

## Project Structure
```
DS_project/
├── main.py                     # Entry point
├── run_agent.sh                # Execution wrapper script
├── agent/
│   ├── config.py               # Centralized configuration (selectors, prompts)
│   ├── utils.py                # Shared utilities
│   ├── interactive_shopping_cli.py
│   ├── coupang_playwright_agent.py
│   ├── coupang_search_agent.py
│   └── infra/
│       └── llm.py              # LLM infrastructure
├── crawling/
│   ├── fetch_html.py
│   ├── review.py
│   ├── inquiries.py
│   ├── quantity.py
│   └── btf.py
└── preprocessing/
    ├── data_chunking_processor.py
    └── clova_ocr_batch.py
```

## Installation

### 1. Create Environment
```bash
conda create -n shopping_env python=3.10
conda activate shopping_env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Variables
Create a `.env` file or export variables:
```bash
export OPENAI_API_KEY="your-api-key"
export CLOVA_OCR_API_URL="..."       # Optional
export CLOVA_OCR_SECRET_KEY="..."    # Optional
```

### 4. Optional: Login Cookie Setup
To reduce the chance of bot‑detection, a logged‑in session cookie may be used. Save it as `cookie.txt` in the project root.

## Usage

### Interactive Mode
The recommended way to run the agent is using the wrapper script:
```bash
./run_agent.sh
```

Or directly via Python:
```bash
python main.py --cookie-file cookie.txt
```

### Options
```bash
# Run in headless mode
./run_agent.sh --headless

# Specify a different cookie file
./run_agent.sh --cookie-file my_cookies.txt

# Enable OCR (requires API keys)
./run_agent.sh --clova-ocr-api-url ... --clova-ocr-secret-key ...
```

## Example Interaction Flow
```
User URL → Intent Classification → Review/Q&A Extraction
→ Grounded Answer → Satisfaction Decision → Optional New Search
→ Product Recommendation → Cart Addition
```

## Korean Examples

### 1. Intent Classification Example 

**사용자 입력:**  
“발볼이 넓은 사람도 신을 수 있을까요? 리뷰에 발볼 얘기가 없어서 걱정돼요.”

**LLM 의도 분류 결과 예시:**  
- intent: `product_question`  
- reasoning: “발볼 적합성에 대한 정보 부족으로 인해 사용자가 추가 확인을 요청함.”  
- extracted_keywords: `발볼`, `적합성`, `편안함`

---

**사용자 입력:**  
“이건 너무 비싼데… 다른 가성비 좋은 제품 있어요?”

**LLM 의도 분류 결과 예시:**  
- intent: `dissatisfaction_price`  
- reasoning: “가격 불만을 명확히 표현했고 대안 요청이 포함됨.”  
- extracted_keywords: `가성비`, `대안`, `저렴한`

### 2. Search Query Generation Example 

**사용자 입력:**  
“조용한 모터 달린 선풍기 없나요? 지금 제품은 소음이 너무 심해요.”

**LLM이 생성하는 검색어 예시:**  
- “저소음 선풍기”  
- “BLDC 선풍기 조용한”  
- “수면용 선풍기 저소음”

**검색 사유:**  
- 사용자는 특정 제품의 소음 문제를 제기했고, 해결 기준이 “소음 감소/정숙성”에 있음.

---

**사용자 입력:**  
“발볼 넓은 남자용 러닝화 추천해줘.”

**LLM 검색어 생성 예시:**  
- “남성 러닝화 발볼 넓은”  
- “4E 러닝화 남자”  
- “와이드핏 남성 운동화”

## Technology Stack

### Core
- Python 3.10+
- Playwright (Coupang page automation)  
- OpenAI GPT models  
- LangChain orchestration  

### Scraping and Data Handling
- BeautifulSoup4  
- httpx / requests  
- asyncio  

### Anti-Bot Measures
- Webdriver masking  
- Cookie‑based session continuity  
- Realistic headers and delays  

## Module Descriptions

### main.py
The application entry point. Handles argument parsing and initializes the interactive CLI.

### agent/config.py
Centralized configuration file containing CSS selectors, LLM prompts, and other constants.

### agent/utils.py
Shared utility functions for file handling, URL parsing, and other common tasks.

### agent/interactive_shopping_cli.py
Manages the dialogue loop, browser operations, and OCR‑optional flows.

### agent/infra/llm.py
Handles LLM initialization and interaction, including intent classification and rationale extraction.

### agent/coupang_playwright_agent.py
Handles:
- Page load & parsing  
- Review / Q&A extraction  
- Answer generation  

### agent/coupang_search_agent.py
Executes:
- Coupang search flows  
- Result extraction & ranking  

## Troubleshooting

### Page Unreachable
Often caused by anti‑bot detection. Renew cookies and retry.

### Timeout Issues
Disable headless mode during debugging to see what's happening in the browser.

### No Search Results
Open browser visually to inspect CSS selectors.

## License
This project is intended for research and educational use only.