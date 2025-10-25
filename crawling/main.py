#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coupang Crawling Pipeline (refactored)
- No sys.argv mutation
- Consistent cookie handling
- Safer step orchestration
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterable

# Step modules
from crawl_category_urls import extract_product_links, fetch_html as fetch_category_html
from make_products_csv import run as make_csv_run
from fetch_html import run_batch as fetch_html_batch
from review import batch_reviews
from inquiries import batch_inquiries
from quantity import batch_quantity, load_products


# ────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────
def load_cookie_text(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        print(f"⚠️  Cookie file not found: {cookie_file}")
        return None
    return p.read_text(encoding="utf-8").strip()


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Paths:
    base_dir: Path
    outputs_dir: Path
    urls_file: Path
    products_csv: Path
    html_dir: Path
    reviews_dir: Path
    inquiries_dir: Path
    quantity_dir: Path
    reviews_jsonl: Path
    inquiries_jsonl: Path
    quantity_jsonl: Path


def build_paths(base_dir: str) -> Paths:
    base = Path(base_dir)
    outputs = ensure_dir(base / "outputs")
    return Paths(
        base_dir=base,
        outputs_dir=outputs,
        urls_file=base / "urls.txt",
        products_csv=base / "products.csv",
        html_dir=ensure_dir(outputs / "html"),
        reviews_dir=ensure_dir(outputs / "reviews"),
        inquiries_dir=ensure_dir(outputs / "inquiries"),
        quantity_dir=ensure_dir(outputs / "quantity"),
        reviews_jsonl=outputs / "reviews" / "reviews.jsonl",
        inquiries_jsonl=outputs / "inquiries" / "inquiries.jsonl",
        quantity_jsonl=outputs / "quantity" / "quantity.jsonl",
    )


# ────────────────────────────────────────────────────
# Pipeline
# ────────────────────────────────────────────────────
class CoupangCrawlingPipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.paths = build_paths(config.get("base_dir", "."))
        self.cookie_file = config.get("cookie_file")
        self.cookie_text = load_cookie_text(self.cookie_file)  # for quantity step

    # Step 1: Crawl category URLs without touching sys.argv
    def step1_crawl_category_urls(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 1: Crawling Category URLs")
        print("=" * 60)

        category_url = self.config.get("category_url")
        url_pattern = self.config.get("url_pattern")
        start_page = int(self.config.get("start_page", 1))
        pages = int(self.config.get("pages", 200))
        sleep_min = float(self.config.get("sleep_min", 2.5))
        sleep_max = float(self.config.get("sleep_max", 5.6))
        max_urls = int(self.config.get("max_urls", 1000))

        if not (category_url or url_pattern):
            print("✗ Either --category-url or --url-pattern must be provided")
            return False

        # page URLs
        def page_urls() -> Iterable[str]:
            if url_pattern:
                for p in range(start_page, start_page + pages):
                    yield url_pattern.format(page=p)
            else:
                sep = "&" if ("?" in (category_url or "")) else "?"
                for p in range(start_page, start_page + pages):
                    yield f"{category_url}{sep}page={p}"

        seen = set()
        write_count = 0
        ensure_dir(self.paths.urls_file.parent)

        with self.paths.urls_file.open("a", encoding="utf-8") as fp:
            for idx, page_url in enumerate(page_urls(), 1):
                print(f"⇒ GET {page_url}")
                html = fetch_category_html(
                    page_url,
                    headers={
                        # minimal headers; crawl_category_urls.build_headers와 동일하게 맞추고 싶다면 가져와도 됨
                        "user-agent": (
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
                        ),
                        "referer": page_url,
                        "origin": "https://www.coupang.com",
                        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                    retries=2,
                )
                urls = extract_product_links(html, base=page_url)
                new_urls = [u for u in urls if u not in seen]
                for u in new_urls:
                    fp.write(u + "\n")
                    seen.add(u)
                    write_count += 1
                    if write_count >= max_urls:
                        print(f"== reached max_urls {max_urls}, stop ==")
                        print(f"✓ Collected {write_count} URLs → {self.paths.urls_file}")
                        return True

                print(f"  (+{len(new_urls)} new) total_unique={len(seen)}")
                time.sleep(random.uniform(sleep_min, sleep_max))

        if write_count > 0:
            print(f"✓ Successfully collected {write_count} product URLs")
            return True
        print("✗ No URLs were collected")
        return False

    def step2_make_products_csv(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 2: Creating Products CSV")
        print("=" * 60)

        if not self.paths.urls_file.exists() or self.paths.urls_file.stat().st_size == 0:
            print("✗ URLs file not found or empty. Run step 1 first.")
            return False

        try:
            make_csv_run(
                in_txt=str(self.paths.urls_file),
                out_csv=str(self.paths.products_csv),
                default_size=self.config.get("default_size", 20),
                do_backfill=self.config.get("do_backfill", True),
                cookie_file=self.cookie_file,
                backfill_limit=self.config.get("backfill_limit"),
            )
            ok = self.paths.products_csv.exists() and self.paths.products_csv.stat().st_size > 0
            print("✓ Successfully created products CSV" if ok else "✗ Failed to create products CSV")
            return ok
        except Exception as e:
            print(f"✗ Error in step 2: {e}")
            return False

    def step3_fetch_html(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 3: Fetching Product HTML")
        print("=" * 60)

        if not self.paths.products_csv.exists():
            print("✗ Products CSV not found. Run step 2 first.")
            return False

        result = fetch_html_batch(
            input_csv=self.paths.products_csv,
            outdir=self.paths.html_dir,
            jsonl_path=self.paths.html_dir / "summary.jsonl",
            cookie_file=self.cookie_file,
            timeout=self.config.get("timeout", 40),
            delay_min=self.config.get("delay_min", 0.8),
            delay_max=self.config.get("delay_max", 1.6),
        )
        ok = (result == 0)
        print("✓ Successfully fetched HTML pages" if ok else "✗ Failed to fetch HTML pages")
        return ok

    def step4_fetch_reviews(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 4: Fetching Product Reviews")
        print("=" * 60)

        if not self.paths.products_csv.exists():
            print("✗ Products CSV not found. Run step 2 first.")
            return False

        try:
            batch_reviews(
                csv_path=str(self.paths.products_csv),
                outdir=str(self.paths.reviews_dir),
                jsonl_path=str(self.paths.reviews_jsonl),
                cookie_file=self.cookie_file,  # review 모듈은 cookie_file 경로를 받음
                retries=self.config.get("retries", 2),
                per_page_sleep=(
                    self.config.get("review_sleep_min", 1.2),
                    self.config.get("review_sleep_max", 2.2),
                ),
            )
            print(f"✓ Successfully fetched reviews → {self.paths.reviews_dir}")
            return True
        except Exception as e:
            print(f"✗ Error in step 4: {e}")
            return False

    def step5_fetch_inquiries(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 5: Fetching Product Inquiries")
        print("=" * 60)

        if not self.paths.products_csv.exists():
            print("✗ Products CSV not found. Run step 2 first.")
            return False

        try:
            batch_inquiries(
                csv_path=str(self.paths.products_csv),
                outdir=str(self.paths.inquiries_dir),
                jsonl_path=str(self.paths.inquiries_jsonl),
                cookie_file=self.cookie_file,  # inquiries 모듈도 cookie_file 경로 사용
                retries=self.config.get("retries", 2),
                per_page_sleep=(
                    self.config.get("inquiry_sleep_min", 1.2),
                    self.config.get("inquiry_sleep_max", 2.2),
                ),
            )
            print(f"✓ Successfully fetched inquiries → {self.paths.inquiries_dir}")
            return True
        except Exception as e:
            print(f"✗ Error in step 5: {e}")
            return False

    def step6_fetch_quantity(self) -> bool:
        print("\n" + "=" * 60)
        print("STEP 6: Fetching Quantity Information")
        print("=" * 60)

        if not self.paths.products_csv.exists():
            print("✗ Products CSV not found. Run step 2 first.")
            return False

        try:
            items = load_products(self.paths.products_csv)
            if not items:
                print("✗ No valid products found in CSV")
                return False

            # quantity.batch_quantity 는 cookie **문자열**을 받음
            batch_quantity(
                input_items=items,
                cookie=self.cookie_text,
                outdir=str(self.paths.quantity_dir),
                jsonl_summary=str(self.paths.quantity_jsonl),
                sleep_min=self.config.get("quantity_sleep_min", 1.5),
                sleep_max=self.config.get("quantity_sleep_max", 3.0),
                max_retries=self.config.get("retries", 2),
            )
            print(f"✓ Successfully fetched quantity info → {self.paths.quantity_dir}")
            return True
        except Exception as e:
            print(f"✗ Error in step 6: {e}")
            return False

    def run_pipeline(self, steps: Optional[list] = None) -> bool:
        if steps is None:
            steps = [1, 2, 3, 4, 5, 6]

        print("Starting Coupang Crawling Pipeline")
        print(f"Steps to run: {steps}")
        print(f"Base directory: {self.paths.base_dir}")
        print(f"Cookie file: {self.cookie_file}")

        step_funcs = {
            1: self.step1_crawl_category_urls,
            2: self.step2_make_products_csv,
            3: self.step3_fetch_html,
            4: self.step4_fetch_reviews,
            5: self.step5_fetch_inquiries,
            6: self.step6_fetch_quantity,
        }

        success_count = 0
        for n in steps:
            fn = step_funcs.get(n)
            if not fn:
                print(f"⚠️  Unknown step: {n}")
                continue
            ok = fn()
            if ok:
                success_count += 1
            else:
                print(f"\n⚠️  Step {n} failed. Pipeline may be incomplete.")
                if not self.config.get("continue_on_error", False):
                    break

        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Completed steps: {success_count}/{len(steps)}")
        print(f"Output directory: {self.paths.outputs_dir}")

        if success_count == len(steps):
            print("✓ Pipeline completed successfully!")
            return True
        else:
            print("⚠️  Pipeline completed with some failures")
            return False


# ────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Coupang Crawling Pipeline - Complete data extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python crawling/main.py --category_url "https://www.coupang.com/np/categories/XXXX" --cookie_file cookie.txt
  python crawling/main.py --url_pattern "https://www.coupang.com/np/categories/XXXX?page={page}" --cookie_file cookie.txt
  python crawling/main.py --category_url "..." --steps 1,2,3 --continue_on_error
        """,
    )

    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument("--category_url")
    url_group.add_argument("--url_pattern")

    parser.add_argument("--cookie_file")
    parser.add_argument("--base_dir", default=".")
    parser.add_argument("--steps", help="Comma-separated list of steps (1-6)")
    parser.add_argument("--continue_on_error", action="store_true")

    # step 1
    parser.add_argument("--max_urls", type=int, default=100)
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--start_page", type=int, default=1)
    parser.add_argument("--sleep_min", type=float, default=2.5)
    parser.add_argument("--sleep_max", type=float, default=5.6)

    # step 2
    parser.add_argument("--default_size", type=int, default=20)
    parser.add_argument("--no_backfill", action="store_true")
    parser.add_argument("--backfill-limit", type=int)

    # step 3
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--delay_min", type=float, default=0.8)
    parser.add_argument("--delay_max", type=float, default=1.6)

    # steps 4-6
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--review_sleep_min", type=float, default=1.2)
    parser.add_argument("--review_sleep_max", type=float, default=2.2)
    parser.add_argument("--inquiry_sleep_min", type=float, default=1.2)
    parser.add_argument("--inquiry_sleep_max", type=float, default=2.2)
    parser.add_argument("--quantity_sleep_min", type=float, default=1.5)
    parser.add_argument("--quantity_sleep_max", type=float, default=3.0)

    return parser.parse_args()


def main():
    args = parse_args()

    # steps parse
    if args.steps:
        try:
            steps = [int(s.strip()) for s in args.steps.split(",")]
            if not all(1 <= s <= 6 for s in steps):
                print("Error: Steps must be 1..6")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid steps format. Use comma-separated numbers (e.g., 1,2,3)")
            sys.exit(1)
    else:
        steps = None

    config = {
        "category_url": args.category_url,
        "url_pattern": args.url_pattern,
        "cookie_file": args.cookie_file,
        "base_dir": args.base_dir,
        "continue_on_error": args.continue_on_error,
        # step 1
        "max_urls": args.max_urls,
        "pages": args.pages,
        "start_page": args.start_page,
        "sleep_min": args.sleep_min,
        "sleep_max": args.sleep_max,
        # step 2
        "default_size": args.default_size,
        "do_backfill": not args.no_backfill,
        "backfill_limit": args.backfill_limit,
        # step 3
        "timeout": args.timeout,
        "delay_min": args.delay_min,
        "delay_max": args.delay_max,
        # steps 4-6
        "retries": args.retries,
        "review_sleep_min": args.review_sleep_min,
        "review_sleep_max": args.review_sleep_max,
        "inquiry_sleep_min": args.inquiry_sleep_min,
        "inquiry_sleep_max": args.inquiry_sleep_max,
        "quantity_sleep_min": args.quantity_sleep_min,
        "quantity_sleep_max": args.quantity_sleep_max,
    }

    pipeline = CoupangCrawlingPipeline(config)
    try:
        ok = pipeline.run_pipeline(steps)
        sys.exit(0 if ok else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Pipeline failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
