# Coupang Crawling Pipeline

This pipeline provides a complete solution for crawling Coupang product data, from category pages to detailed product information including reviews, inquiries, and quantity data.

## Pipeline Overview

The pipeline consists of 6 main steps:

1. **URL Collection** (`crawl_category_urls.py`) - Extract product URLs from category pages
2. **CSV Creation** (`make_products_csv.py`) - Convert URLs to structured CSV with product IDs
3. **HTML Fetching** (`fetch_html.py`) - Download product detail HTML pages
4. **Review Extraction** (`review.py`) - Extract product reviews
5. **Inquiry Extraction** (`inquiries.py`) - Extract product Q&A/inquiries
6. **Quantity Information** (`quantity.py`) - Extract stock/quantity data

## Quick Start

### Basic Usage

```bash
# Run complete pipeline with category URL
python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --cookie-file cookie.txt

# Run with URL pattern for pagination
python main.py --url-pattern "https://www.coupang.com/np/categories/XXXX?page={page}" --cookie-file cookie.txt
```

### Run Specific Steps

```bash
# Run only steps 1-3 (URL collection, CSV creation, HTML fetching)
python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --steps 1,2,3 --cookie-file cookie.txt

# Run only data extraction steps (4-6)
python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --steps 4,5,6 --cookie-file cookie.txt
```

### Advanced Configuration

```bash
# Custom limits and timing
python main.py \
  --category-url "https://www.coupang.com/np/categories/XXXX" \
  --max-urls 500 \
  --pages 50 \
  --sleep-min 3.0 \
  --sleep-max 6.0 \
  --cookie-file cookie.txt

# Custom output directory
python main.py \
  --category-url "https://www.coupang.com/np/categories/XXXX" \
  --base-dir /path/to/output \
  --cookie-file cookie.txt
```

## Configuration Options

### Required Arguments
- `--category-url` or `--url-pattern`: Source URL for crawling
- `--cookie-file`: Path to cookie file for authentication

### Optional Arguments

#### General
- `--base-dir`: Base directory for outputs (default: current directory)
- `--steps`: Comma-separated list of steps to run (1-6, default: all)
- `--continue-on-error`: Continue pipeline even if some steps fail

#### Step 1: URL Collection
- `--max-urls`: Maximum number of URLs to collect (default: 1000)
- `--pages`: Number of pages to crawl (default: 200)
- `--start-page`: Starting page number (default: 1)
- `--sleep-min`/`--sleep-max`: Sleep between requests (default: 2.5-5.6s)

#### Step 2: CSV Creation
- `--default-size`: Default page size for products (default: 20)
- `--no-backfill`: Disable HTML backfill for missing IDs
- `--backfill-limit`: Limit number of products to backfill

#### Step 3: HTML Fetching
- `--timeout`: Request timeout in seconds (default: 40)
- `--delay-min`/`--delay-max`: Delay between HTML requests (default: 0.8-1.6s)

#### Steps 4-6: Data Extraction
- `--retries`: Number of retries for failed requests (default: 2)
- `--review-sleep-min`/`--review-sleep-max`: Sleep between review requests (default: 1.2-2.2s)
- `--inquiry-sleep-min`/`--inquiry-sleep-max`: Sleep between inquiry requests (default: 1.2-2.2s)
- `--quantity-sleep-min`/`--quantity-sleep-max`: Sleep between quantity requests (default: 1.5-3.0s)

## Output Structure

```
outputs/
├── html/                    # Product detail HTML pages
│   ├── response_*.html
│   └── summary.jsonl
├── reviews/                 # Product reviews
│   ├── review_*.json
│   └── reviews.jsonl
├── inquiries/               # Product Q&A/inquiries
│   ├── inquiries_*.json
│   └── inquiries.jsonl
└── quantity/                # Stock/quantity information
    ├── quantity_info_*.json
    └── quantity.jsonl
```

## Cookie File Setup

1. Open Coupang website in your browser
2. Login to your account
3. Open Developer Tools (F12)
4. Go to Application/Storage tab
5. Copy all cookies and save to a text file
6. Use the file path with `--cookie-file` option

## Error Handling

- The pipeline includes robust error handling and retry mechanisms
- Failed requests are logged with detailed error messages
- Use `--continue-on-error` to continue even if some steps fail
- Each step can be run independently for debugging

## Performance Tips

- Adjust sleep times based on your needs and server response
- Use smaller `--max-urls` for testing
- Consider running steps separately for large datasets
- Monitor output directories for disk space usage

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure cookie file is valid and up-to-date
2. **Rate Limiting**: Increase sleep times between requests
3. **Network Timeouts**: Increase timeout values
4. **Missing Product IDs**: Enable backfill with `--no-backfill` flag

### Debug Mode

Run individual steps to isolate issues:

```bash
# Test URL collection only
python main.py --category-url "URL" --steps 1 --cookie-file cookie.txt

# Test CSV creation only (requires existing urls.txt)
python main.py --category-url "URL" --steps 2 --cookie-file cookie.txt
```

## Dependencies

Make sure you have all required Python packages installed:

```bash
pip install requests beautifulsoup4 urllib3
```

Optional packages for better performance:
```bash
pip install httpx h2  # For HTTP/2 support
```
