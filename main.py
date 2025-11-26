#!/usr/bin/env python3
"""
Main entry point for the Coupang Shopping Assistant.
"""

import asyncio
import os
import sys
import argparse
from agent.interactive_shopping_cli import InteractiveShoppingCLI

async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Interactive shopping assistant with AI")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--cookie-file", help="Path to cookie file for authentication")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)", default="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")
    parser.add_argument(
        "--run-dir",
        help="Root directory to store collected product data (default: outputs/scenario_runs)",
    )
    parser.add_argument(
        "--clova-ocr-api-url",
        help="CLOVA OCR API URL (default: 환경 변수 CLOVA_OCR_API_URL)",
    )
    parser.add_argument(
        "--clova-ocr-secret-key",
        help="CLOVA OCR Secret Key (default: 환경 변수 CLOVA_OCR_SECRET_KEY)",
    )
    parser.add_argument(
        "--clova-ocr-delay",
        type=float,
        default=0.5,
        help="CLOVA OCR API 호출 사이 대기 시간(초)",
    )

    args = parser.parse_args()

    # Check for API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key가 필요합니다.")
        print("환경 변수 OPENAI_API_KEY를 설정하거나 --api-key 옵션을 사용하세요.")
        sys.exit(1)

    cli = InteractiveShoppingCLI(
        headless=args.headless,
        cookie_file=args.cookie_file,
        api_key=api_key,
        run_dir=args.run_dir,
        clova_ocr_api_url=args.clova_ocr_api_url,
        clova_ocr_secret_key=args.clova_ocr_secret_key,
        clova_ocr_delay=args.clova_ocr_delay,
    )

    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 종료합니다.")
