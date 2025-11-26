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
from urllib3.util.retry import Retry
import logging
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# ── 기본값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/products/inquiries"
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

def build_referer(product_id: str,
                  item_id: Optional[str] = None,
                  vendor_item_id: Optional[str] = None) -> str:
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
    }
    if cookie:
        h["cookie"] = cookie
    return h

def build_params(product_id: str, page_no: int = 1, is_preview: bool = True) -> Dict[str, str]:
    return {"productId": product_id, "pageNo": str(page_no), "isPreview": "true" if is_preview else "false"}

def save_json(obj, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / filename
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

# ── 네트워킹 ─────────────────────────────────────────
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

def safe_request(url: str, headers: Dict[str, str], params: Dict[str, str], retries: int = 2) -> requests.Response:
    """짧은 타임아웃 + 지수 백오프. session 재시도로 1차 방어, 여기서 추가 백오프."""
    sess = make_session(retries=retries)
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return sess.get(url, headers=headers, params=params, timeout=(5, 10))
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
def fetch_inquiries(product_id: str,
                    page_no: int = 1,
                    cookie: Optional[str] = None,
                    item_id: Optional[str] = None,
                    vendor_item_id: Optional[str] = None,
                    outdir: Optional[str] = None,
                    retries: int = 2,
                    is_preview: bool = True):
    referer = build_referer(product_id, item_id, vendor_item_id)
    headers = build_headers(referer, cookie)
    params = build_params(product_id, page_no, is_preview)

    logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

    resp = safe_request(URL, headers, params, retries=retries)
    logger.debug("status: %s url: %s", resp.status_code, resp.url)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    if outdir:
        ts = int(time.time() * 1000)
        p = save_json(data, Path(outdir), f"inquiries_{product_id}_p{page_no}_{ts}.json")
        logger.info("saved → %s", p)

    return resp, data

