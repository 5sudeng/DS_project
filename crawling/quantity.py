#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import random
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import requests
import logging

logger = logging.getLogger(__name__)

URL = "https://www.coupang.com/next-api/products/quantity-info"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# ─────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────
def _read_cookie_text(cookie: Optional[str], cookie_file: Optional[str]) -> Optional[str]:
    if cookie and cookie.strip():
        return cookie
    if cookie_file:
        p = Path(cookie_file)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    return None

def build_headers(referer: str, cookie: Optional[str] = None) -> Dict[str, str]:
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": UA,
        "referer": referer,
        "origin": "https://www.coupang.com",
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
        "connection": "keep-alive",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "x-coupang-target-market": "KR",
        "x-coupang-accept-language": "ko-KR",
    }
    if cookie:
        h["cookie"] = cookie
    return h

def build_params(product_id: str, item_id: str, vendor_item_id: str) -> Dict[str, str]:
    return {
        "productId": product_id,
        "vendorItemId": vendor_item_id,
        "deliveryToggle": "false",
        "landingItemId": item_id,
        "landingProductId": product_id,
        "landingVendorItemId": vendor_item_id,
    }

def referer_url(product_id: str, item_id: str, vendor_item_id: str) -> str:
    return f"https://www.coupang.com/vp/products/{product_id}?itemId={item_id}&vendorItemId={vendor_item_id}"

def save_json(obj, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / filename
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path

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

# ─────────────────────────────────────────────────────
# Fetch core (httpx → requests → curl)
# ─────────────────────────────────────────────────────
def _try_httpx(headers: Dict[str, str], params: Dict[str, str], timeout_s: int) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
    try:
        import httpx
    except Exception:
        return None, None, None, None
    try:
        client = httpx.Client(
            http2=True, headers=headers, params=params,
            timeout=httpx.Timeout(15.0, connect=5.0, read=float(timeout_s), write=float(timeout_s)),
            follow_redirects=True
        )
        with client as c:
            r = c.get(URL)
        text = r.text or ""
        if r.status_code == 200 and text:
            ctype = r.headers.get("content-type", "")
            data = r.json() if ctype.startswith("application/json") else {"raw_text": text}
            logger.debug("[httpx/h2] status: %s url: %s", r.status_code, r.url)
            return r.status_code, str(r.url), text, data
        else:
            raise RuntimeError(f"httpx/h2 unexpected status {r.status_code}")
    except Exception as e:
        logger.warning("[httpx/h2] failed: %s", e)
        return None, None, None, None

def _try_requests(headers: Dict[str, str], params: Dict[str, str], retries: int = 3) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(URL, headers=headers, params=params, timeout=(5, 10))
            text = r.text or ""
            if r.status_code == 200 and text:
                ctype = r.headers.get("content-type", "")
                data = r.json() if "application/json" in ctype else {"raw_text": text}
                logger.debug("[requests] status: %s url: %s", r.status_code, r.url)
                return r.status_code, r.url, text, data
            else:
                raise RuntimeError(f"requests unexpected status {r.status_code}")
        except requests.Timeout as e:
            last_err = e
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
            logger.warning("[requests retry %d/%d] timeout -> wait %.2fs", attempt, retries, delay)
            time.sleep(delay)
        except requests.RequestException as e:
            last_err = e
            logger.warning("[requests retry %d/%d] error: %s", attempt, retries, e)
            time.sleep(1.0)
    logger.warning("[requests] failed: %s", last_err)
    return None, None, None, None

def _try_curl(headers: Dict[str, str], params: Dict[str, str], timeout_s: int, outdir: Path) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
    from urllib.parse import urlencode
    full_url = URL + "?" + urlencode(params)
    tmp_path = outdir / "_curl_quantity_tmp.json"
    # 공통 -H 플래그 구성
    header_flags: List[str] = []
    for k in [
        "accept","accept-language","user-agent","referer","origin","x-requested-with",
        "sec-fetch-mode","sec-fetch-site","sec-fetch-dest","sec-ch-ua","sec-ch-ua-platform",
        "sec-ch-ua-mobile","connection","x-coupang-target-market","x-coupang-accept-language"
    ]:
        if k in headers:
            header_flags += ["-H", f"{k}: {headers[k]}"]

    curl_cmd = [
        "curl","--silent","--show-error","--location",
        "--http1.1","--ipv4","--compressed",
        "--connect-timeout","5","--max-time", str(max(15, int(timeout_s))),
        *header_flags, full_url, "-o", str(tmp_path)
    ]
    logger.info("[fallback] curl: %s", " ".join(shlex.quote(c) for c in curl_cmd))
    try:
        subprocess.run(curl_cmd, check=True)
    except subprocess.CalledProcessError as ce:
        logger.warning("[fallback] curl exit: %s", ce.returncode)

    if tmp_path.exists() and tmp_path.stat().st_size > 0:
        raw = tmp_path.read_text(encoding="utf-8", errors="ignore")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw_text": raw}
        logger.info("[fallback] curl read from file")
        return 200, full_url, raw, data
    return None, None, None, None

# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────
def fetch_quantity_info(
    product_id: str,
    item_id: str,
    vendor_item_id: str,
    cookie: Optional[str] = None,
    timeout: int = 60,
    outdir: Optional[str] = ".",
    filename_prefix: str = "quantity_info",
):
    """
    Fetch /next-api/products/quantity-info with robust fallbacks.
    Returns (resp_like, data). Always saves JSON to <outdir>/<prefix>_<pid>_<ts>.json
    """
    ref = referer_url(product_id, item_id, vendor_item_id)
    headers = build_headers(ref, cookie)
    params = build_params(product_id, item_id, vendor_item_id)

    print("[REQUEST]", URL)
    print("  referer:", ref)
    print("  params :", params)

    out_dir = Path(outdir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    with IPv4OnlyResolver():
        # 1) httpx/h2
        status, url, text, data = _try_httpx(headers, params, timeout)
        # 2) requests
        if data is None:
            status, url, text, data = _try_requests(headers, params, retries=3)
        # 3) curl
        if data is None:
            status, url, text, data = _try_curl(headers, params, timeout, out_dir)

    if data is None:
        raise RuntimeError("failed to fetch quantity-info")

    ts = int(time.time() * 1000)
    out_path = save_json(data, out_dir, f"{filename_prefix}_{product_id}_{ts}.json")
    logger.info("Fetched quantity info: status=%s len=%d saved=%s", status, len(text) if text else 0, out_path)

    class _Resp: pass
    resp = _Resp()
    resp.status_code = status
    resp.url = url
    return resp, data

