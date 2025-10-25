#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import random
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# ─────────────────────────────────────────────────────
# URL/HTML 파싱 관련 정규식
# ─────────────────────────────────────────────────────
ID_PATTERNS = [
    (re.compile(r'"landingItemId"\s*:\s*(\d+)'), "itemId"),
    (re.compile(r'"landingVendorItemId"\s*:\s*(\d+)'), "vendorItemId"),
    (re.compile(r'"itemId"\s*:\s*(\d+)'), "itemId"),
    (re.compile(r'"vendorItemId"\s*:\s*(\d+)'), "vendorItemId"),
    (re.compile(r'"itemIdList"\s*:\s*\[\s*(\d+)'), "itemId"),
    (re.compile(r'"vendorItemIdList"\s*:\s*\[\s*(\d+)'), "vendorItemId"),
    (re.compile(r'data-item-id\s*=\s*"(\d+)"'), "itemId"),
    (re.compile(r'data-vendor-item-id\s*=\s*"(\d+)"'), "vendorItemId"),
]
_UHEX = re.compile(r"\\u([0-9a-fA-F]{4})")
_ADD_TO_CART_RX = re.compile(r'"addToCartUrl"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)
_QS_PAIR_RX = re.compile(
    r'(?:\?|&)(itemId|landingItemId|vendorItemId|landingVendorItemId)=(\d+)', re.I
)

# ─────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────
def load_cookie(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {path}")
    return p.read_text(encoding="utf-8").strip()

def build_headers(referer: str, cookie: Optional[str]) -> Dict[str, str]:
    h = {
        "user-agent": UA,
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": referer,
        "origin": "https://www.coupang.com",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "navigate",
        "sec-fetch-dest": "document",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "accept-encoding": "gzip, deflate, br",
        "connection": "keep-alive",
    }
    if cookie:
        h["cookie"] = cookie
    return h

class IPv4OnlyResolver:
    """일부 CDN의 IPv6 이슈 회피용 임시 패치"""
    def __enter__(self):
        import socket
        self._socket = socket
        self._orig = socket.getaddrinfo

        def _ipv4_only(*a, **k):
            res = self._orig(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res

        socket.getaddrinfo = _ipv4_only
        return self

    def __exit__(self, *exc):
        self._socket.getaddrinfo = self._orig

def make_session(retries: int) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        backoff_factor=0.8,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def fetch_html(url: str, headers: Dict[str, str],
               retries: int = 2, connect_to: int = 8, read_to: int = 20) -> str:
    last_exc: Optional[Exception] = None
    with IPv4OnlyResolver():
        sess = make_session(retries)
        for attempt in range(retries + 1):
            try:
                r = sess.get(url, headers=headers, timeout=(connect_to, read_to), allow_redirects=True)
                r.raise_for_status()
                return r.text
            except requests.Timeout as e:
                last_exc = e
                delay = (2 ** attempt) * 0.7 + random.uniform(0, 0.8)
                print(f"[backfill retry {attempt+1}/{retries+1}] timeout → wait {delay:.2f}s")
                time.sleep(delay)
            except requests.RequestException as e:
                last_exc = e
                if attempt < retries:
                    delay = (2 ** attempt) * 0.7 + random.uniform(0, 0.8)
                    print(f"[backfill retry {attempt+1}/{retries+1}] error: {e} → wait {delay:.2f}s")
                    time.sleep(delay)
                else:
                    break

    # 최종 폴백: curl(HTTP/1.1 + IPv4 + 압축)
    tmp_path = Path("_curl_backfill_tmp.html").absolute()
    curl_cmd = [
        "curl", "--silent", "--show-error", "--location",
        "--http1.1", "--ipv4", "--compressed",
        "--connect-timeout", str(connect_to),
        "--max-time", str(max(read_to, connect_to + 10)),
    ]
    for k, v in headers.items():
        curl_cmd += ["-H", f"{k}: {v}"]
    curl_cmd += [url, "-o", str(tmp_path)]
    print("[fallback] curl:", " ".join(shlex.quote(c) for c in curl_cmd))
    try:
        import subprocess
        subprocess.run(curl_cmd, check=True)
    except Exception as ce:
        print("[fallback] curl exit/error:", ce)
    if tmp_path.exists() and tmp_path.stat().st_size > 0:
        return tmp_path.read_text(encoding="utf-8", errors="ignore")
    raise last_exc or RuntimeError("request failed")

# ─────────────────────────────────────────────────────
# HTML → itemId / vendorItemId 파싱
# ─────────────────────────────────────────────────────
def _unescape_text(s: str) -> str:
    import html as _html
    t = _html.unescape(s)
    t = _UHEX.sub(lambda m: chr(int(m.group(1), 16)), t)
    return (t.replace(r"\/", "/")
             .replace(r"\t", "\t")
             .replace(r"\r", "\r")
             .replace(r"\n", "\n"))

def _extract_from_addtocart(html: str) -> Tuple[str, str]:
    m = _ADD_TO_CART_RX.search(html)
    if not m:
        return "", ""
    raw = m.group(1)
    try:
        u = json.loads(f'"{raw}"')  # 안전 디코딩
    except Exception:
        u = _unescape_text(raw)

    # URL 규격화
    if u.startswith("coupang://"):
        u = "https://dummy/" + u[len("coupang://"):]
    if not re.match(r'^[a-z]+://', u, re.I):
        u = "https://dummy/" + u.lstrip("/")

    try:
        pu = urlparse(u)
        qs = parse_qs(pu.query)
        item = (qs.get("itemId") or qs.get("landingItemId") or [""])[0]
        vend = (qs.get("vendorItemId") or qs.get("landingVendorItemId") or [""])[0]
        if item or vend:
            return item, vend
    except Exception:
        pass

    item = vend = ""
    for k, v in _QS_PAIR_RX.findall(u):
        kl = k.lower()
        if not item and kl in ("itemid", "landingitemid"):
            item = v
        if not vend and kl in ("vendoritemid", "landingvendoritemid"):
            vend = v
    return item, vend

def parse_missing_ids_from_html(html: str, current_item: str, current_vendor: str) -> Tuple[str, str]:
    item_id, vendor_item_id = current_item or "", current_vendor or ""
    if not html:
        return item_id, vendor_item_id

    # 0) addToCartUrl 우선
    ai, av = _extract_from_addtocart(html)
    item_id = item_id or ai
    vendor_item_id = vendor_item_id or av
    if item_id and vendor_item_id:
        return item_id, vendor_item_id

    # 1) 패턴 스캔
    for rx, kind in ID_PATTERNS:
        m = rx.search(html)
        if m:
            if kind == "itemId" and not item_id:
                item_id = m.group(1)
            elif kind == "vendorItemId" and not vendor_item_id:
                vendor_item_id = m.group(1)
        if item_id and vendor_item_id:
            return item_id, vendor_item_id

    # 2) <script> 블록 내부 재시도(+ addToCartUrl)
    for script_blob in re.findall(r"<script[^>]*>\s*(.*?)\s*</script>", html, flags=re.S | re.I):
        if not (item_id and vendor_item_id):
            ai, av = _extract_from_addtocart(script_blob)
            item_id = item_id or ai
            vendor_item_id = vendor_item_id or av
            if item_id and vendor_item_id:
                return item_id, vendor_item_id

        for rx, kind in ID_PATTERNS:
            m = rx.search(script_blob)
            if m:
                if kind == "itemId" and not item_id:
                    item_id = m.group(1)
                elif kind == "vendorItemId" and not vendor_item_id:
                    vendor_item_id = m.group(1)
            if item_id and vendor_item_id:
                return item_id, vendor_item_id

    # 3) 언이스케이프 텍스트에서 쿼리 파편 스캔
    text2 = _unescape_text(html)
    if not item_id:
        m = re.search(r'(?:\?|&)(?:itemId|landingItemId)=(\d+)', text2, re.I)
        if m:
            item_id = m.group(1)
    if not vendor_item_id:
        m = re.search(r'(?:\?|&)(?:vendorItemId|landingVendorItemId)=(\d+)', text2, re.I)
        if m:
            vendor_item_id = m.group(1)

    return item_id, vendor_item_id

# ─────────────────────────────────────────────────────
# Step 1) URL에서 ID 추출
# ─────────────────────────────────────────────────────
def extract_ids(url: str) -> Optional[Tuple[str, str, str]]:
    url = url.strip()
    if not url:
        return None
    pu = urlparse(url)
    m = re.search(r"/vp/products/(\d+)", pu.path)
    if not m:
        return None
    product_id = m.group(1)
    qs = parse_qs(pu.query)
    item_id = (qs.get("itemId") or qs.get("landingItemId") or [""])[0]
    vendor_item_id = (qs.get("vendorItemId") or qs.get("landingVendorItemId") or [""])[0]
    return product_id, item_id, vendor_item_id

# ─────────────────────────────────────────────────────
# Step 2) 백필(HTML 방문)로 누락 ID 채우기
# ─────────────────────────────────────────────────────
def fill_missing_ids(rows: List[Dict[str, str]], cookie_file: Optional[str] = None,
                     limit: Optional[int] = None) -> List[Dict[str, str]]:
    cookie = load_cookie(cookie_file)
    filled = 0
    for row in rows:
        if row.get("itemId") and row.get("vendorItemId"):
            continue
        if limit is not None and filled >= limit:
            break

        pid = row["productId"]
        url = f"https://www.coupang.com/vp/products/{pid}"
        try:
            html = fetch_html(url, build_headers(url, cookie), retries=2, connect_to=6, read_to=12)
            txt_path = f"{pid}.html"
            Path(txt_path).write_text(html, encoding="utf-8", errors="ignore")
            print(f"[debug] saved HTML text -> {txt_path}")

            new_item, new_vendor = parse_missing_ids_from_html(
                html, row.get("itemId", ""), row.get("vendorItemId", "")
            )
            if new_item and not row.get("itemId"):
                row["itemId"] = new_item
            if new_vendor and not row.get("vendorItemId"):
                row["vendorItemId"] = new_vendor

            print(f"filled → {pid}: item={row.get('itemId','')}, vendor={row.get('vendorItemId','')}")
            filled += 1
        except Exception as e:
            print(f"[fill-skip] {pid} → {e}")

        # be gentle
        time.sleep(random.uniform(0.4, 0.9))
    return rows

# ─────────────────────────────────────────────────────
# Step 3) Main
# ─────────────────────────────────────────────────────
def run(in_txt: str, out_csv: str, default_size: int = 20,
        do_backfill: bool = True, cookie_file: Optional[str] = None,
        backfill_limit: Optional[int] = None) -> None:
    rows: List[Dict[str, str]] = []
    seen = set()

    with open(in_txt, encoding="utf-8") as f:
        for line in f:
            r = extract_ids(line)
            if not r:
                msg = line.strip()
                if msg:
                    print(f"[skip] not a product url: {msg}")
                continue
            pid, iid, vid = r
            key = (pid, iid, vid)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "productId": pid,
                "itemId": iid,
                "vendorItemId": vid,
                "startPage": 1,
                "pages": 1,
                "size": default_size,
            })

    if do_backfill:
        print(f"backfill missing itemId/vendorItemId (rows={len(rows)}) …")
        rows = fill_missing_ids(rows, cookie_file=cookie_file, limit=backfill_limit)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["productId", "itemId", "vendorItemId", "startPage", "pages", "size"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows → {out_csv}")

def parse_args(argv: List[str]):
    # 의존성 없이도 되지만, 표준 argparse가 더 견고합니다.
    import argparse
    p = argparse.ArgumentParser(description="Make Coupang products.csv from URLs (with optional backfill).")
    p.add_argument("in_txt", nargs="?", default="urls.txt", help="input text file (one URL per line)")
    p.add_argument("out_csv", nargs="?", default="products.csv", help="output csv path")
    p.add_argument("--no-backfill", action="store_true", help="disable HTML backfill")
    p.add_argument("--cookie", type=str, default=None, help="cookie file path")
    p.add_argument("--size", type=int, default=20, help="default page size")
    p.add_argument("--limit", type=int, default=None, help="max rows to backfill")
    return p.parse_args(argv)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    run(
        in_txt=args.in_txt,
        out_csv=args.out_csv,
        default_size=args.size,
        do_backfill=not args.no_backfill,
        cookie_file=args.cookie,
        backfill_limit=args.limit,
    )
