#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coupang Crawling Pipeline
=========================

This script orchestrates the entire Coupang crawling pipeline:
1. crawl_category_urls.py -> Extract product URLs from category pages
2. make_products_csv.py -> Convert URLs to structured CSV with product IDs
3. fetch_html.py -> Download product detail HTML pages
4. review.py -> Extract product reviews
5. inquiries.py -> Extract product inquiries/Q&A
6. quantity.py -> Extract quantity/stock information

Usage:
    python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --cookie-file cookie.txt
    python main.py --url-pattern "https://www.coupang.com/np/categories/XXXX?page={page}" --cookie-file cookie.txt
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Import all the crawling modules
from crawl_category_urls import main as crawl_urls_main, extract_product_links, fetch_html as fetch_category_html
from make_products_csv import run as make_csv_run
from fetch_html import run_batch as fetch_html_batch
from review import batch_reviews
from inquiries import batch_inquiries
from quantity import batch_quantity, load_products

class CoupangCrawlingPipeline:
    """Main pipeline orchestrator for Coupang crawling"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_dir = Path(config.get('base_dir', '.'))
        self.cookie_file = config.get('cookie_file')
        
        # Create output directories
        self.outputs_dir = self.base_dir / 'outputs'
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Intermediate files
        self.urls_file = self.base_dir / 'urls.txt'
        self.products_csv = self.base_dir / 'products.csv'
        
        # Output directories for each stage
        self.html_dir = self.outputs_dir / 'html'
        self.reviews_dir = self.outputs_dir / 'reviews'
        self.inquiries_dir = self.outputs_dir / 'inquiries'
        self.quantity_dir = self.outputs_dir / 'quantity'
        
        # Summary files
        self.reviews_jsonl = self.reviews_dir / 'reviews.jsonl'
        self.inquiries_jsonl = self.inquiries_dir / 'inquiries.jsonl'
        self.quantity_jsonl = self.quantity_dir / 'quantity.jsonl'
        
    def step1_crawl_category_urls(self) -> bool:
        """Step 1: Extract product URLs from category pages"""
        print("\n" + "="*60)
        print("STEP 1: Crawling Category URLs")
        print("="*60)
        
        try:
            # Prepare arguments for crawl_category_urls
            sys.argv = [
                'crawl_category_urls.py',
                '--out', str(self.urls_file),
                '--max', str(self.config.get('max_urls', 1000)),
                '--pages', str(self.config.get('pages', 200)),
                '--start-page', str(self.config.get('start_page', 1)),
                '--sleep-min', str(self.config.get('sleep_min', 2.5)),
                '--sleep-max', str(self.config.get('sleep_max', 5.6)),
            ]
            
            if self.cookie_file:
                sys.argv.extend(['--cookie-file', self.cookie_file])
            
            if self.config.get('category_url'):
                sys.argv.extend(['--category-url', self.config['category_url']])
            elif self.config.get('url_pattern'):
                sys.argv.extend(['--url-pattern', self.config['url_pattern']])
            else:
                print("Error: Either --category-url or --url-pattern must be provided")
                return False
            
            # Run the URL crawling
            crawl_urls_main()
            
            # Check if URLs were collected
            if self.urls_file.exists() and self.urls_file.stat().st_size > 0:
                url_count = len(self.urls_file.read_text(encoding='utf-8').strip().split('\n'))
                print(f"✓ Successfully collected {url_count} product URLs")
                return True
            else:
                print("✗ No URLs were collected")
                return False
                
        except Exception as e:
            print(f"✗ Error in step 1: {e}")
            return False
    
    def step2_make_products_csv(self) -> bool:
        """Step 2: Convert URLs to structured CSV"""
        print("\n" + "="*60)
        print("STEP 2: Creating Products CSV")
        print("="*60)
        
        try:
            if not self.urls_file.exists():
                print("✗ URLs file not found. Run step 1 first.")
                return False
            
            # Run make_products_csv
            make_csv_run(
                in_txt=str(self.urls_file),
                out_csv=str(self.products_csv),
                default_size=self.config.get('default_size', 20),
                do_backfill=self.config.get('do_backfill', True),
                cookie_file=self.cookie_file,
                backfill_limit=self.config.get('backfill_limit')
            )
            
            if self.products_csv.exists() and self.products_csv.stat().st_size > 0:
                print(f"✓ Successfully created products CSV: {self.products_csv}")
                return True
            else:
                print("✗ Failed to create products CSV")
                return False
                
        except Exception as e:
            print(f"✗ Error in step 2: {e}")
            return False
    
    def step3_fetch_html(self) -> bool:
        """Step 3: Download product detail HTML pages"""
        print("\n" + "="*60)
        print("STEP 3: Fetching Product HTML")
        print("="*60)
        
        try:
            if not self.products_csv.exists():
                print("✗ Products CSV not found. Run step 2 first.")
                return False
            
            # Run fetch_html batch
            result = fetch_html_batch(
                input_csv=self.products_csv,
                outdir=self.html_dir,
                jsonl_path=self.html_dir / 'summary.jsonl',
                cookie_file=self.cookie_file,
                timeout=self.config.get('timeout', 40),
                delay_min=self.config.get('delay_min', 0.8),
                delay_max=self.config.get('delay_max', 1.6)
            )
            
            if result == 0:
                print(f"✓ Successfully fetched HTML pages to: {self.html_dir}")
                return True
            else:
                print("✗ Failed to fetch HTML pages")
                return False
                
        except Exception as e:
            print(f"✗ Error in step 3: {e}")
            return False
    
    def step4_fetch_reviews(self) -> bool:
        """Step 4: Extract product reviews"""
        print("\n" + "="*60)
        print("STEP 4: Fetching Product Reviews")
        print("="*60)
        
        try:
            if not self.products_csv.exists():
                print("✗ Products CSV not found. Run step 2 first.")
                return False
            
            # Run batch reviews
            batch_reviews(
                csv_path=str(self.products_csv),
                outdir=str(self.reviews_dir),
                jsonl_path=str(self.reviews_jsonl),
                cookie_file=self.cookie_file,
                retries=self.config.get('retries', 2),
                per_page_sleep=(self.config.get('review_sleep_min', 1.2), 
                              self.config.get('review_sleep_max', 2.2))
            )
            
            print(f"✓ Successfully fetched reviews to: {self.reviews_dir}")
            return True
                
        except Exception as e:
            print(f"✗ Error in step 4: {e}")
            return False
    
    def step5_fetch_inquiries(self) -> bool:
        """Step 5: Extract product inquiries/Q&A"""
        print("\n" + "="*60)
        print("STEP 5: Fetching Product Inquiries")
        print("="*60)
        
        try:
            if not self.products_csv.exists():
                print("✗ Products CSV not found. Run step 2 first.")
                return False
            
            # Run batch inquiries
            batch_inquiries(
                csv_path=str(self.products_csv),
                outdir=str(self.inquiries_dir),
                jsonl_path=str(self.inquiries_jsonl),
                cookie_file=self.cookie_file,
                retries=self.config.get('retries', 2),
                per_page_sleep=(self.config.get('inquiry_sleep_min', 1.2), 
                              self.config.get('inquiry_sleep_max', 2.2))
            )
            
            print(f"✓ Successfully fetched inquiries to: {self.inquiries_dir}")
            return True
                
        except Exception as e:
            print(f"✗ Error in step 5: {e}")
            return False
    
    def step6_fetch_quantity(self) -> bool:
        """Step 6: Extract quantity/stock information"""
        print("\n" + "="*60)
        print("STEP 6: Fetching Quantity Information")
        print("="*60)
        
        try:
            if not self.products_csv.exists():
                print("✗ Products CSV not found. Run step 2 first.")
                return False
            
            # Load products and run batch quantity
            items = load_products(self.products_csv)
            if not items:
                print("✗ No valid products found in CSV")
                return False
            
            batch_quantity(
                input_items=items,
                cookie=self.cookie_file,
                outdir=str(self.quantity_dir),
                jsonl_summary=str(self.quantity_jsonl),
                sleep_min=self.config.get('quantity_sleep_min', 1.5),
                sleep_max=self.config.get('quantity_sleep_max', 3.0),
                max_retries=self.config.get('retries', 2)
            )
            
            print(f"✓ Successfully fetched quantity info to: {self.quantity_dir}")
            return True
                
        except Exception as e:
            print(f"✗ Error in step 6: {e}")
            return False
    
    def run_pipeline(self, steps: Optional[list] = None) -> bool:
        """Run the complete crawling pipeline"""
        if steps is None:
            steps = [1, 2, 3, 4, 5, 6]  # All steps by default
        
        print("Starting Coupang Crawling Pipeline")
        print(f"Steps to run: {steps}")
        print(f"Base directory: {self.base_dir}")
        print(f"Cookie file: {self.cookie_file}")
        
        step_functions = {
            1: self.step1_crawl_category_urls,
            2: self.step2_make_products_csv,
            3: self.step3_fetch_html,
            4: self.step4_fetch_reviews,
            5: self.step5_fetch_inquiries,
            6: self.step6_fetch_quantity,
        }
        
        success_count = 0
        for step_num in steps:
            if step_num in step_functions:
                if step_functions[step_num]():
                    success_count += 1
                else:
                    print(f"\n⚠️  Step {step_num} failed. Pipeline may be incomplete.")
                    if not self.config.get('continue_on_error', False):
                        break
            else:
                print(f"⚠️  Unknown step: {step_num}")
        
        print("\n" + "="*60)
        print("PIPELINE SUMMARY")
        print("="*60)
        print(f"Completed steps: {success_count}/{len(steps)}")
        print(f"Output directory: {self.outputs_dir}")
        
        if success_count == len(steps):
            print("✓ Pipeline completed successfully!")
            return True
        else:
            print("⚠️  Pipeline completed with some failures")
            return False


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Coupang Crawling Pipeline - Complete data extraction from category to detailed product info",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with category URL
  python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --cookie-file cookie.txt
  
  # Using URL pattern for pagination
  python main.py --url-pattern "https://www.coupang.com/np/categories/XXXX?page={page}" --cookie-file cookie.txt
  
  # Run only specific steps
  python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --steps 1,2,3 --cookie-file cookie.txt
  
  # Custom configuration
  python main.py --category-url "https://www.coupang.com/np/categories/XXXX" --max-urls 500 --pages 50 --cookie-file cookie.txt
        """
    )
    
    # Required arguments
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument('--category-url', help='Category URL to crawl (e.g., https://www.coupang.com/np/categories/XXXX)')
    url_group.add_argument('--url-pattern', help='URL pattern with {page} placeholder for pagination')
    
    # Optional arguments
    parser.add_argument('--cookie-file', help='Path to cookie file for authentication')
    parser.add_argument('--base-dir', default='.', help='Base directory for outputs (default: current directory)')
    parser.add_argument('--steps', help='Comma-separated list of steps to run (1-6, default: all)')
    parser.add_argument('--continue-on-error', action='store_true', help='Continue pipeline even if some steps fail')
    
    # Step 1: URL crawling
    parser.add_argument('--max-urls', type=int, default=1000, help='Maximum number of URLs to collect (default: 1000)')
    parser.add_argument('--pages', type=int, default=200, help='Number of pages to crawl (default: 200)')
    parser.add_argument('--start-page', type=int, default=1, help='Starting page number (default: 1)')
    parser.add_argument('--sleep-min', type=float, default=2.5, help='Minimum sleep between requests (default: 2.5s)')
    parser.add_argument('--sleep-max', type=float, default=5.6, help='Maximum sleep between requests (default: 5.6s)')
    
    # Step 2: CSV creation
    parser.add_argument('--default-size', type=int, default=20, help='Default page size for products (default: 20)')
    parser.add_argument('--no-backfill', action='store_true', help='Disable HTML backfill for missing IDs')
    parser.add_argument('--backfill-limit', type=int, help='Limit number of products to backfill')
    
    # Step 3: HTML fetching
    parser.add_argument('--timeout', type=int, default=40, help='Request timeout in seconds (default: 40)')
    parser.add_argument('--delay-min', type=float, default=0.8, help='Minimum delay between HTML requests (default: 0.8s)')
    parser.add_argument('--delay-max', type=float, default=1.6, help='Maximum delay between HTML requests (default: 1.6s)')
    
    # Steps 4-6: Data extraction
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for failed requests (default: 2)')
    parser.add_argument('--review-sleep-min', type=float, default=1.2, help='Min sleep between review requests (default: 1.2s)')
    parser.add_argument('--review-sleep-max', type=float, default=2.2, help='Max sleep between review requests (default: 2.2s)')
    parser.add_argument('--inquiry-sleep-min', type=float, default=1.2, help='Min sleep between inquiry requests (default: 1.2s)')
    parser.add_argument('--inquiry-sleep-max', type=float, default=2.2, help='Max sleep between inquiry requests (default: 2.2s)')
    parser.add_argument('--quantity-sleep-min', type=float, default=1.5, help='Min sleep between quantity requests (default: 1.5s)')
    parser.add_argument('--quantity-sleep-max', type=float, default=3.0, help='Max sleep between quantity requests (default: 3.0s)')
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Parse steps
    if args.steps:
        try:
            steps = [int(s.strip()) for s in args.steps.split(',')]
            if not all(1 <= s <= 6 for s in steps):
                print("Error: Steps must be between 1 and 6")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid steps format. Use comma-separated numbers (e.g., 1,2,3)")
            sys.exit(1)
    else:
        steps = None  # All steps
    
    # Build configuration
    config = {
        'category_url': args.category_url,
        'url_pattern': args.url_pattern,
        'cookie_file': args.cookie_file,
        'base_dir': args.base_dir,
        'continue_on_error': args.continue_on_error,
        
        # Step 1
        'max_urls': args.max_urls,
        'pages': args.pages,
        'start_page': args.start_page,
        'sleep_min': args.sleep_min,
        'sleep_max': args.sleep_max,
        
        # Step 2
        'default_size': args.default_size,
        'do_backfill': not args.no_backfill,
        'backfill_limit': args.backfill_limit,
        
        # Step 3
        'timeout': args.timeout,
        'delay_min': args.delay_min,
        'delay_max': args.delay_max,
        
        # Steps 4-6
        'retries': args.retries,
        'review_sleep_min': args.review_sleep_min,
        'review_sleep_max': args.review_sleep_max,
        'inquiry_sleep_min': args.inquiry_sleep_min,
        'inquiry_sleep_max': args.inquiry_sleep_max,
        'quantity_sleep_min': args.quantity_sleep_min,
        'quantity_sleep_max': args.quantity_sleep_max,
    }
    
    # Create and run pipeline
    pipeline = CoupangCrawlingPipeline(config)
    
    try:
        success = pipeline.run_pipeline(steps)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
