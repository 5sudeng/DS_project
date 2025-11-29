#!/usr/bin/env python3
"""
Main entry point for the Coupang Shopping Assistant.
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from interface.cli import ShoppingCLI

async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Interactive shopping assistant with AI")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--cookie-file", help="Path to cookie file for authentication")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument(
        "--run-dir",
        help="Root directory to store collected product data (default: outputs/scenario_runs)",
    )
    parser.add_argument(
        "--ocr-delay",
        type=float,
        default=0.5,
        help="OCR API 호출 사이 대기 시간(초)",
    )

    args = parser.parse_args()

    # Load API Key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        secret_file = Path(".secret")
        if secret_file.exists():
            api_key = secret_file.read_text().strip()

    if not api_key:
        ### check
        print("Error: OpenAI API Key is required.") 
        ### check
        print("Please provide it via --api-key, OPENAI_API_KEY env var, or .secret file.")
        sys.exit(1)

    cli = ShoppingCLI(
        headless=args.headless,
        cookie_file=args.cookie_file,
        api_key=api_key,
        run_dir=args.run_dir,
        ocr_delay=args.ocr_delay,
    )

    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 종료합니다.")
