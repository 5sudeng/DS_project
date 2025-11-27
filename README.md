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

### 4. Multimodal RAG with Vision API
- **NEW**: Automatically extracts product images from detail pages.
- Sends relevant images to GPT-4o-mini Vision API alongside text.
- Enables answering questions about ingredients, nutrition facts, and other image-based information.
- Smart image selection based on text similarity scores.

### 5. Multi‑Turn Conversational Interface
- Maintains conversation history across steps.
- Supports iterative refinement of user preferences.
- Allows optional automated cart addition.

## Project Structure
```
DS_project/
├── main.py                     # Entry point
├── run_agent.sh                # Execution wrapper script
├── config/
│   ├── settings.py             # LLM prompts and general settings
│   └── selectors.py            # CSS selectors
├── core/
│   ├── utils.py                # Shared utilities
│   ├── state.py                # Conversation state management
│   └── cookies.py              # Cookie handling
├── interface/
│   ├── cli/                    # CLI Package
│   │   ├── controller.py       # Main CLI controller
│   │   └── mixins/             # Feature mixins (Browser, Search, Intent)
│   └── artifacts/              # Artifacts Package
│       ├── collector.py        # Main artifact collector
│       └── handlers/           # Handlers for specific tasks (BTF, OCR, Chunking)
├── services/
│   ├── llm_service.py          # LLM interaction service
│   ├── browser_service.py      # Playwright browser service
│   ├── search_service.py       # Product search service
│   └── browser_setup.py        # Browser initialization
├── scrapers/
│   ├── html_fetcher.py         # HTML fetching
│   ├── review_scraper.py       # Review scraping
│   ├── inquiry_scraper.py      # Inquiry scraping
│   ├── quantity_scraper.py     # Quantity/Stock scraping
│   └── product_detail_scraper.py # BTF (Below-The-Fold) scraping
└── processors/
    ├── chunker.py              # Content chunking
    └── ocr_processor.py        # OCR processing
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
- **`OPENAI_API_KEY`**: OpenAI API 키 (필수). `.secret` 파일에 저장하거나 환경 변수로 설정할 수 있습니다.

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
- OpenAI GPT-4o-mini (Text and **Vision API**)  
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

### config/
Contains configuration files:
- `settings.py`: LLM prompts and general settings.
- `selectors.py`: CSS selectors for DOM interaction.

### core/
Core utilities and state management:
- `utils.py`: Shared utility functions.
- `state.py`: Manages conversation state.
- `cookies.py`: Handles cookie loading and parsing.

### interface/
User interface and artifact collection:
- `cli/`:
    - `controller.py`: Main `ShoppingCLI` class orchestrating the interaction.
    - `mixins/`: Contains `BrowserMixin`, `SearchMixin`, and `IntentMixin` for modular functionality.
- `artifacts/`:
    - `collector.py`: Orchestrates the collection of product data.
    - `handlers/`: Specialized handlers for BTF content, OCR, and data chunking.

### services/
Business logic services:
- `llm_service.py`: Handles LLM interactions (intent classification, query generation).
- `browser_service.py`: Manages Playwright browser interactions for product pages.
- `search_service.py`: Handles product search and result parsing.

### scrapers/
Atomic scraping modules for specific data types:
- `html_fetcher.py`, `review_scraper.py`, `inquiry_scraper.py`, `quantity_scraper.py`, `product_detail_scraper.py`.

### processors/
Data processing modules:
- `chunker.py`: Chunks text data for RAG or analysis. **Now includes image path metadata for multimodal RAG**.
- `ocr_processor.py`: Handles OCR tasks using OpenAI GPT-4o Vision.

## Key Features Deep Dive

### Multimodal RAG System

The assistant now supports **vision-enabled question answering** by automatically including relevant product images in LLM prompts.

#### How It Works
```
1. Product images downloaded from BTF (Below-The-Fold) API
2. Image URL → local path mapping stored in context
3. Chunker adds image paths to metadata
4. During Q&A:
   - Text similarity selects relevant chunks
   - Images from selected chunks extracted
   - Up to 3 images encoded as base64
   - Sent to GPT-4o-mini Vision API with question
```

#### Example Use Cases
- **"성분을 알려줘"** (Tell me the ingredients)
  - System includes product detail images
  - Vision API reads ingredient list from image
  - Provides accurate answer even if OCR failed

- **"영양 성분표 보여줘"** (Show me nutrition facts)
  - Relevant nutrition label images included
  - LLM describes nutritional information

#### Cost Optimization
- Images sent with `detail: "low"` (~85 tokens per image)
- Maximum 3 images per question
- Automatic fallback to text-only if no images available

#### Configuration
No additional setup required! Images are automatically:
- Downloaded during product data collection
- Linked to text chunks via metadata
- Selected and sent based on relevance  

## Troubleshooting

### Page Unreachable
Often caused by anti‑bot detection. Renew cookies and retry.

### Timeout Issues
Disable headless mode during debugging to see what's happening in the browser.

### No Search Results
Open browser visually to inspect CSS selectors.

## License
This project is intended for research and educational use only.