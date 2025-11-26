#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import random
import shlex
import socket
import subprocess
import time
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────
def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def build_headers(base_url: str, item_id: str, vendor_item_id: str, cookie: Optional[str]) -> dict:
    h = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "user-agent": UA,
        "referer": f"{base_url}?itemId={item_id}&vendorItemId={vendor_item_id}",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "cache-control": "max-age=0",
    }
    if cookie:
        h["cookie"] = cookie
    return h

class IPv4OnlyResolver:
    """일부 CDN의 IPv6 tar-pit 회피용 DNS 강제기."""
    def __enter__(self):
        self._orig = socket.getaddrinfo
        def _ipv4_only(*a, **k):
            res = self._orig(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res
        socket.getaddrinfo = _ipv4_only
        return self
    def __exit__(self, *exc):
        socket.getaddrinfo = self._orig

def make_requests_session(retries: int = 2) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=retries, connect=retries, read=retries, status=retries,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def print_get(u: str, p: Optional[dict]):
    logger.debug("GET %s params=%s", u, p)

# ─────────────────────────────────────────────────────
# Fetch core
# ─────────────────────────────────────────────────────
def _candidate_urls(product_id: str, item_id: str, vendor_item_id: str) -> Tuple[str, List[Tuple[str, Optional[dict]]]]:
    base_url = f"https://www.coupang.com/vp/products/{product_id}"
    params_full = {"itemId": item_id, "vendorItemId": vendor_item_id}
    cands = [
        (base_url, None),              # no params
        (base_url, params_full),       # with ids
        (base_url, {"pageSize": "1"}), # tiny page variant
    ]
    return base_url, cands

def _try_httpx(candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict, timeout: int) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    try:
        import httpx  # optional
    except Exception:
        return None, None, None

    try:
        import h2  # noqa: F401
        use_http2 = True
    except Exception:
        use_http2 = False

    for u, p in candidates:
        print_get(u, p)
        for attempt in range(1, 4):
            try:
                timeout_cfg = httpx.Timeout(timeout=float(timeout), connect=10.0, read=float(timeout), write=float(timeout), pool=5.0)
                with httpx.Client(http2=use_http2, headers=headers, timeout=timeout_cfg, follow_redirects=True) as client:
                    r = client.get(u, params=p)
                    if r.status_code == 200 and r.text:
                        logger.debug("[httpx/%s] status: %s url: %s", 'h2' if use_http2 else 'h1', r.status_code, r.url)
                        return r.status_code, str(r.url), r.text
                    else:
                        raise RuntimeError(f"httpx status {r.status_code}")
            except Exception as e:
                delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                logger.warning("[httpx] failed (attempt %d/3): %s, wait %.2fs", attempt, e, delay)
                if attempt < 3:
                    time.sleep(delay)
    return None, None, None

def _try_requests(candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict, timeout: int) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    sess = make_requests_session(retries=3)
    for u, p in candidates:
        print_get(u, p)
        for attempt in range(1, 4):
            try:
                r = sess.get(u, headers=headers, params=p, timeout=(10, timeout), allow_redirects=True)
                if r.status_code == 200 and r.text:
                    logger.debug("[requests] status: %s url: %s", r.status_code, r.url)
                    return r.status_code, r.url, r.text
                else:
                    raise RuntimeError(f"HTTP {r.status_code}")
            except requests.Timeout as e:
                delay = (2 ** attempt) + random.uniform(1, 2)
                logger.warning("[retry %d/3] timeout, wait %.2fs", attempt, delay)
                time.sleep(delay)
            except requests.RequestException as e:
                delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                logger.warning("[retry %d/3] request error: %s, wait %.2fs", attempt, e, delay)
                time.sleep(delay)
    return None, None, None

def _try_curl(candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict, timeout: int, product_id: str, cookie: Optional[str]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    tmp_path = Path(f"_curl_html_{product_id}.html").absolute()
    # Prebuild common -H flags
    header_flags = []
    for k in ["accept", "accept-language", "accept-encoding", "user-agent", "origin", "referer", "sec-ch-ua", "sec-ch-ua-platform", "sec-ch-ua-mobile", "connection"]:
        if k in headers:
            header_flags += ["-H", f"{k}: {headers[k]}"]
    if cookie:
        header_flags += ["-H", f"cookie: {cookie}"]

    for u, p in candidates:
        qs = ("?" + urlencode(p)) if p else ""
        full_url = u + qs
        curl_cmd = [
            "curl", "--silent", "--show-error", "--location",
            "--http1.1", "--ipv4", "--compressed",
            "--connect-timeout", "5",
            "--max-time", str(max(15, int(timeout))),
            *header_flags, full_url, "-o", str(tmp_path)
        ]
        logger.info("[fallback] curl: %s", " ".join(shlex.quote(c) for c in curl_cmd))
        try:
            subprocess.run(curl_cmd, check=True)
        except subprocess.CalledProcessError as ce:
            logger.warning("[fallback] curl exit: %s", ce.returncode)

        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            return 200, full_url, tmp_path.read_text(encoding="utf-8", errors="ignore")
    return None, None, None

def fetch_html(
    product_id: str,
    item_id: str,
    vendor_item_id: str,
    timeout: int = 60,
    cookie: Optional[str] = None,
    outdir: Optional[Path] = None,
) -> Tuple[object, BeautifulSoup, Path]:
    """
    Fetch Coupang product HTML with conservative defaults (timeouts, retries, IPv4 workaround).
    Returns (response_like, BeautifulSoup, saved_path).
    response_like has attributes (status_code, url, text).
    Always saves raw HTML to <outdir or CWD>/response_<product_id>.html
    """
    base_url, candidates = _candidate_urls(product_id, item_id, vendor_item_id)
    headers = build_headers(base_url, item_id, vendor_item_id, cookie)

    with IPv4OnlyResolver():
        status, url, text = _try_httpx(candidates, headers, timeout)
        if text is None:
            status, url, text = _try_requests(candidates, headers, timeout)
        if text is None:
            status, url, text = _try_curl(candidates, headers, timeout, product_id, cookie)

    if text is None:
        raise RuntimeError("failed to fetch html")

    # Save & parse
    save_dir = outdir if outdir else Path.cwd()
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / f"response_{product_id}.html"
    out_path.write_text(text, encoding="utf-8")

    out_path.write_text(text, encoding="utf-8")

    logger.info("Fetched HTML: status=%s len=%d saved=%s", status, len(text), out_path)

    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.text.strip() if soup.title else "(no title)"
    logger.debug("Page title: %s", title)

    resp_like = SimpleNamespace(status_code=status, url=url, text=text)
    return resp_like, soup, out_path

