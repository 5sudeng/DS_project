"""Playwright bootstrap utilities for the interactive CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence

from playwright.async_api import Browser, BrowserContext, Page, Playwright

ANTIDETECTION_SCRIPT = """
// Override webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Override plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// Override languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['ko-KR', 'ko', 'en-US', 'en']
});

// Override chrome runtime
window.chrome = {
    runtime: {}
};

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

DEFAULT_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--ignore-certificate-errors",
    # HTTP/2 protocol error workarounds
    "--disable-http2",  # Disable HTTP/2 protocol
    "--disable-quic",   # Disable QUIC protocol
    "--enable-features=NetworkService,NetworkServiceInProcess",  # Use in-process network service
]


@dataclass
class BrowserSessionConfig:
    headless: bool = False
    cookie_header: str | None = None
    cookie_records: Sequence[Dict[str, Any]] = ()


@dataclass
class BrowserSession:
    browser: Browser
    context: BrowserContext
    page: Page
    applied_cookie_count: int = 0


async def bootstrap_browser(playwright: Playwright, config: BrowserSessionConfig) -> BrowserSession:
    """Launch Chromium with Coupang-friendly defaults and return a ready page."""

    browser = await playwright.chromium.launch(headless=config.headless, args=DEFAULT_LAUNCH_ARGS)

    extra_headers = {"Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"}
    if config.cookie_header:
        extra_headers["Cookie"] = config.cookie_header

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        ),
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        extra_http_headers=extra_headers,
    )

    applied_cookie_count = 0
    if config.cookie_records:
        await context.add_cookies(list(config.cookie_records))
        applied_cookie_count = len(config.cookie_records)

    page = await context.new_page()
    await page.add_init_script(ANTIDETECTION_SCRIPT)

    return BrowserSession(
        browser=browser,
        context=context,
        page=page,
        applied_cookie_count=applied_cookie_count,
    )
