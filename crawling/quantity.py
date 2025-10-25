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
            print("[httpx/h2] status:", r.status_code)
            print("[httpx/h2] url   :", str(r.url))
            return r.status_code, str(r.url), text, data
        else:
            raise RuntimeError(f"httpx/h2 unexpected status {r.status_code}")
    except Exception as e:
        print("[httpx/h2] failed:", e)
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
                print("[requests] status:", r.status_code)
                print("[requests] url   :", r.url)
                return r.status_code, r.url, text, data
            else:
                raise RuntimeError(f"requests unexpected status {r.status_code}")
        except requests.Timeout as e:
            last_err = e
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
            print(f"[requests retry {attempt}/{retries}] timeout -> wait {delay:.2f}s")
            time.sleep(delay)
        except requests.RequestException as e:
            last_err = e
            print(f"[requests retry {attempt}/{retries}] error:", e)
            time.sleep(1.0)
    print("[requests] failed:", last_err)
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
    print("[fallback] curl:", " ".join(shlex.quote(c) for c in curl_cmd))
    try:
        subprocess.run(curl_cmd, check=True)
    except subprocess.CalledProcessError as ce:
        print("[fallback] curl exit:", ce.returncode)

    if tmp_path.exists() and tmp_path.stat().st_size > 0:
        raw = tmp_path.read_text(encoding="utf-8", errors="ignore")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw_text": raw}
        print("[fallback] curl read from file")
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
    print("status:", status)
    print("url   :", url)
    print("len   :", len(text) if text is not None else 0)
    print(f"saved → {out_path}")

    class _Resp: pass
    resp = _Resp()
    resp.status_code = status
    resp.url = url
    return resp, data

# ─────────────────────────────────────────────────────
# Batch helpers
# ─────────────────────────────────────────────────────
def load_products(path: Path) -> List[Tuple[str, str, str]]:
    """
    CSV: productId,itemId,vendorItemId (대소문자 무관)
    JSONL: 각 라인 객채에 동일 키
    """
    items: List[Tuple[str, str, str]] = []
    ext = path.suffix.lower()
    if ext == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = (row.get("productId") or row.get("productid") or "").strip()
                iid = (row.get("itemId") or row.get("itemid") or "").strip()
                vid = (row.get("vendorItemId") or row.get("vendoritemid") or "").strip()
                if pid and iid and vid:
                    items.append((pid, iid, vid))
    elif ext in (".jsonl", ".ndjson"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                pid = str(obj.get("productId", "")).strip()
                iid = str(obj.get("itemId", "")).strip()
                vid = str(obj.get("vendorItemId", "")).strip()
                if pid and iid and vid:
                    items.append((pid, iid, vid))
    else:
        raise ValueError("CSV 또는 JSONL 지원")
    return items

def batch_quantity(
    input_items: Sequence[Tuple[str, str, str]],
    cookie: Optional[str],
    outdir: str,
    jsonl_summary: Optional[str] = None,
    sleep_min: float = 1.5,
    sleep_max: float = 3.0,
    max_retries: int = 2,
):
    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_fp = Path(jsonl_summary).open("a", encoding="utf-8") if jsonl_summary else None
    total, ok, fail = len(input_items), 0, 0

    for idx, (pid, iid, vid) in enumerate(input_items, 1):
        print(f"\n[{idx}/{total}] productId={pid} itemId={iid} vendorItemId={vid}")
        attempt = 0
        while True:
            try:
                resp, data = fetch_quantity_info(
                    pid, iid, vid, cookie=cookie, timeout=60, outdir=str(out_dir), filename_prefix="quantity_info"
                )
                if resp.status_code == 200:
                    ok += 1
                    if jsonl_fp:
                        jsonl_fp.write(json.dumps(
                            {"productId": pid, "itemId": iid, "vendorItemId": vid, "response": data},
                            ensure_ascii=False
                        ) + "\n")
                    break
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}")
            except Exception as e:
                attempt += 1
                if attempt > max_retries:
                    fail += 1
                    print(f"실패 (retries exhausted): {e}")
                    break
                delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
                print(f"재시도 {attempt}/{max_retries}... {delay:.2f}s 대기 ({e})")
                time.sleep(delay)
        time.sleep(random.uniform(sleep_min, sleep_max))

    if jsonl_fp:
        jsonl_fp.close()

    print(f"\n== 완료: 성공 {ok} / 실패 {fail} / 총 {total} ==")
    if fail:
        sys.exit(2)

# ─────────────────────────────────────────────────────
# Quick probe (유지)
# ─────────────────────────────────────────────────────
def quick_probe(product_id: str, item_id: str, vendor_item_id: str, cookie: Optional[str] = None):
    ref = referer_url(product_id, item_id, vendor_item_id)
    headers = build_headers(ref, cookie)
    params = build_params(product_id, item_id, vendor_item_id)
    print("[PROBE] HEAD 5/5 no-redirects")
    try:
        r = requests.head(URL, headers=headers, params=params, timeout=(5, 5), allow_redirects=False)
        print("  status:", r.status_code)
    except Exception as e:
        print("  HEAD error:", e)
    print("[PROBE] GET 5/8 short")
    try:
        r = requests.get(URL, headers=headers, params=params, timeout=(5, 8))
        print("  status:", r.status_code, "len:", len(r.content))
    except Exception as e:
        print("  GET error:", e)

# ─────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Coupang quantity-info fetcher (single/batch)")
    p.add_argument("--product_id", dest="product_id", help="단일 실행: productId")
    p.add_argument("--item_id", dest="item_id", help="단일 실행: itemId")
    p.add_argument("--vendor_item_id", dest="vendor_item_id", help="단일 실행: vendorItemId")
    p.add_argument("--input", "-i", help="배치 실행 입력 파일 (CSV 또는 JSONL)")
    p.add_argument("--outdir", "-o", default="outputs_quantity", help="응답 JSON 저장 경로")
    p.add_argument("--jsonl", help="요약 JSONL 출력")
    p.add_argument("--cookie", help="쿠키 문자열")
    p.add_argument("--cookie_file", help="쿠키 텍스트 파일 경로")
    p.add_argument("--sleep_min", type=float, default=1.5, help="요청 사이 최소 대기(초)")
    p.add_argument("--sleep_max", type=float, default=3.0, help="요청 사이 최대 대기(초)")
    p.add_argument("--retries", type=int, default=2, help="실패 시 재시도 횟수")
    return p.parse_args()

def main():
    args = parse_args()
    cookie = _read_cookie_text(args.cookie, args.cookie_file)

    if args.input:
        items = load_products(Path(args.input))
        if not items:
            sys.exit(1)
        batch_quantity(
            items, cookie=cookie, outdir=args.outdir, jsonl_summary=args.jsonl,
            sleep_min=args.sleep_min, sleep_max=args.sleep_max, max_retries=args.retries
        )
    else:
        if not (args.product_id and args.item_id and args.vendor_item_id):
            sys.exit(1)
        fetch_quantity_info(
            args.product_id, args.item_id, args.vendor_item_id,
            cookie=cookie, timeout=60, outdir=args.outdir
        )

if __name__ == "__main__":
    main()
