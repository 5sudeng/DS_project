"""Utility to capture Coupang cookies via Playwright."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from .browser import BrowserSessionConfig, bootstrap_browser


async def harvest_cookies(output_path: Path, headless: bool = False) -> None:
    """Launch a browser, let the user log in, then persist cookies to disk."""
    output_path = output_path.expanduser().resolve()
    print(f"📁 쿠키를 {output_path} 에 저장합니다.")

    async with async_playwright() as playwright:
        session = await bootstrap_browser(
            playwright,
            BrowserSessionConfig(headless=headless),
        )
        page = session.page
        try:
            print("🌐 https://www.coupang.com 으로 이동합니다. 로그인해주세요.")
            await page.goto("https://www.coupang.com", wait_until="domcontentloaded")
            input("✅ 쿠팡 로그인이 완료되면 Enter 키를 눌러 쿠키를 저장하세요...")

            state = await session.context.storage_state()
            cookies = state.get("cookies", [])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"🍪 {len(cookies)}개의 쿠키를 저장했습니다.")
        finally:
            await session.browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Coupang cookies for the voice browser.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output path for the cookie JSON file.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the harvesting browser in headless mode (not recommended).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(harvest_cookies(args.output, headless=args.headless))


if __name__ == "__main__":
    main()
