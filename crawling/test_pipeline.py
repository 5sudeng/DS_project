#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the Coupang Crawling Pipeline
This script tests the pipeline with a small sample to verify everything works
"""

import sys
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from main import CoupangCrawlingPipeline

def test_pipeline():
    """Test the pipeline with minimal configuration"""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Testing pipeline in temporary directory: {temp_dir}")
        
        # Test configuration
        config = {
            'category_url': 'https://www.coupang.com/np/categories/194276',  # Electronics category
            'cookie_file': None,  # No cookie for testing
            'base_dir': temp_dir,
            'continue_on_error': True,
            
            # Minimal settings for testing
            'max_urls': 10,  # Very small number for testing
            'pages': 2,      # Just 2 pages
            'start_page': 1,
            'sleep_min': 1.0,
            'sleep_max': 2.0,
            
            'default_size': 5,
            'do_backfill': False,  # Skip backfill for faster testing
            'backfill_limit': None,
            
            'timeout': 20,
            'delay_min': 0.5,
            'delay_max': 1.0,
            
            'retries': 1,
            'review_sleep_min': 0.5,
            'review_sleep_max': 1.0,
            'inquiry_sleep_min': 0.5,
            'inquiry_sleep_max': 1.0,
            'quantity_sleep_min': 0.5,
            'quantity_sleep_max': 1.0,
        }
        
        # Create pipeline
        pipeline = CoupangCrawlingPipeline(config)
        
        print("Testing individual steps...")
        
        # Test step 1: URL collection
        print("\n1. Testing URL collection...")
        try:
            success = pipeline.step1_crawl_category_urls()
            if success:
                print("✓ URL collection test passed")
            else:
                print("✗ URL collection test failed")
                return False
        except Exception as e:
            print(f"✗ URL collection test error: {e}")
            return False
        
        # Test step 2: CSV creation
        print("\n2. Testing CSV creation...")
        try:
            success = pipeline.step2_make_products_csv()
            if success:
                print("✓ CSV creation test passed")
            else:
                print("✗ CSV creation test failed")
                return False
        except Exception as e:
            print(f"✗ CSV creation test error: {e}")
            return False
        
        # Test step 3: HTML fetching (with minimal products)
        print("\n3. Testing HTML fetching...")
        try:
            success = pipeline.step3_fetch_html()
            if success:
                print("✓ HTML fetching test passed")
            else:
                print("✗ HTML fetching test failed")
                return False
        except Exception as e:
            print(f"✗ HTML fetching test error: {e}")
            return False
        
        print("\n✓ All basic tests passed!")
        print("Note: Steps 4-6 (reviews, inquiries, quantity) require valid product IDs")
        print("and may fail without proper authentication cookies.")
        
        return True

def test_configuration():
    """Test configuration parsing"""
    print("Testing configuration parsing...")
    
    # Test with minimal config
    config = {
        'category_url': 'https://example.com',
        'cookie_file': None,
        'base_dir': '.',
    }
    
    try:
        pipeline = CoupangCrawlingPipeline(config)
        print("✓ Configuration test passed")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    print("Coupang Crawling Pipeline Test")
    print("=" * 40)
    
    # Test configuration first
    if not test_configuration():
        sys.exit(1)
    
    # Test pipeline
    if not test_pipeline():
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("✓ All tests passed! Pipeline is ready to use.")
    print("\nTo run the full pipeline:")
    print("python main.py --category-url 'YOUR_URL' --cookie-file cookie.txt")
