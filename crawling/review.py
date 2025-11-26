#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import random
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
import logging

logger = logging.getLogger(__name__)

# ── 기본값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/review"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# ── 유틸 ─────────────────────────────────────────────
def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def build_referer(product_id: str, item_id: Optional[str] = None, vendor_item_id: Optional[str] = None) -> str:
    base = f"https://www.coupang.com/vp/products/{product_id}"
    return f"{base}?itemId={item_id}&vendorItemId={vendor_item_id}" if (item_id and vendor_item_id) else base

def build_headers(product_detail_url: str, cookie: Optional[str]) -> Dict[str, str]:
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": UA,
        "origin": "https://www.coupang.com",
        "referer": product_detail_url,
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "x-coupang-target-market": "KR",
        "x-coupang-accept-language": "ko-KR",
        "connection": "keep-alive",
    }
    if cookie:
        h["cookie"] = cookie
    return h

def build_params(product_id: str,
                 vendor_item_id: Optional[str] = None,
                 item_id: Optional[str] = None,
                 page: int = 1,
                 size: int = 10) -> Dict[str, str]:
    params = {"productId": product_id, "page": str(page), "size": str(size)}
    if vendor_item_id:
        params["vendorItemId"] = vendor_item_id
        params["landingVendorItemId"] = vendor_item_id
    if item_id:
        params["landingItemId"] = item_id
        params["landingProductId"] = product_id
    return params

def save_json(obj, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / filename
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

# ── 네트워크 공통(안정성 강화) ────────────────────────
class IPv4OnlyResolver:
    """일부 CDN의 IPv6 tar-pit 회피용(선택)."""
    def __enter__(self):
        self._orig = socket.getaddrinfo
        def _ipv4_only(*a, **k):
            res = self._orig(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res
        socket.getaddrinfo = _ipv4_only
        return self
    def __exit__(self, *exc):
        socket.getaddrinfo = self._orig

def make_session(retries: int = 2) -> requests.Session:
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

def safe_request(url: str, headers: Dict[str, str], params: Dict[str, str], retries: int = 2):
    """Session 재시도 + 추가 지수 백오프 + IPv4 강제."""
    sess = make_session(retries=retries)
    last_err = None
    with IPv4OnlyResolver():
        for attempt in range(retries + 1):
            try:
                return sess.get(url, headers=headers, params=params, timeout=(5, 12))
            except requests.Timeout as e:
                last_err = e
                delay = (2 ** attempt) * 0.8 + random.uniform(0, 0.6)
                logger.warning("[retry %d/%d] timeout → wait %.2fs", attempt + 1, retries, delay)
                time.sleep(delay)
            except requests.RequestException as e:
                last_err = e
                logger.warning("[retry %d/%d] error: %s", attempt + 1, retries, e)
                time.sleep(1.0)
    raise last_err or RuntimeError("request failed")

# ── 단일 호출 ────────────────────────────────────────
def fetch_reviews(product_id: str,
                  vendor_item_id: Optional[str] = None,
                  item_id: Optional[str] = None,
                  cookie: Optional[str] = None,
                  page: int = 1,
                  size: int = 10,
                  outdir: Optional[str] = None,
                  retries: int = 2):
    referer = build_referer(product_id, item_id, vendor_item_id)
    headers = build_headers(referer, cookie)
    params = build_params(product_id, vendor_item_id, item_id, page, size)

    logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

    resp = safe_request(URL, headers, params, retries=retries)
    logger.debug("status: %s url: %s", resp.status_code, resp.url)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    if outdir:
        ts = int(time.time() * 1000)
        p = save_json(data, Path(outdir), f"review_{product_id}_p{page}_{ts}.json")
        logger.info("saved → %s", p)

    return resp, data

