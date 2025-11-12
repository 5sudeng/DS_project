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
    print("⇒ GET", u)
    if p:
        print("   params:", p)

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
                        print(f"[httpx/{'h2' if use_http2 else 'h1'}] status:", r.status_code)
                        print(f"[httpx/{'h2' if use_http2 else 'h1'}] url   :", str(r.url))
                        return r.status_code, str(r.url), r.text
                    else:
                        raise RuntimeError(f"httpx status {r.status_code}")
            except Exception as e:
                delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                print(f"[httpx] failed (attempt {attempt}/3): {e}, wait {delay:.2f}s")
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
                    print("[requests] status:", r.status_code)
                    print("[requests] url   :", r.url)
                    return r.status_code, r.url, r.text
                else:
                    raise RuntimeError(f"HTTP {r.status_code}")
            except requests.Timeout as e:
                delay = (2 ** attempt) + random.uniform(1, 2)
                print(f"[retry {attempt}/3] timeout, wait {delay:.2f}s")
                time.sleep(delay)
            except requests.RequestException as e:
                delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                print(f"[retry {attempt}/3] request error: {e}, wait {delay:.2f}s")
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
        print("[fallback] curl:", " ".join(shlex.quote(c) for c in curl_cmd))
        try:
            subprocess.run(curl_cmd, check=True)
        except subprocess.CalledProcessError as ce:
            print("[fallback] curl exit:", ce.returncode)

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

    print("status:", status)
    print("url   :", url)
    print("len   :", len(text))
    print("saved →", out_path)

    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.text.strip() if soup.title else "(no title)"
    print("title:", title)

    resp_like = SimpleNamespace(status_code=status, url=url, text=text)
    return resp_like, soup, out_path

# ─────────────────────────────────────────────────────
# Runners
# ─────────────────────────────────────────────────────
def run_single(
    product_id: str,
    item_id: str,
    vendor_item_id: str,
    outdir: Path,
    cookie_file: Optional[str],
    timeout: int,
) -> int:
    cookie = load_cookie(cookie_file) if cookie_file else None
    resp, soup, out_path = fetch_html(
        product_id, item_id, vendor_item_id, timeout=timeout, cookie=cookie, outdir=outdir
    )
    print(f"saved -> {out_path}")
    return 0

def run_batch(
    input_csv: Path,
    outdir: Path,
    jsonl_path: Optional[Path],
    cookie_file: Optional[str],
    timeout: int,
    delay_min: float,
    delay_max: float,
) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    cookie = load_cookie(cookie_file) if cookie_file else None

    rows = list(csv.DictReader(input_csv.open(newline="", encoding="utf-8")))
    print(f"== 총 {len(rows)}개 상품 처리 ==")

    stats_ok = 0
    summary = []

    for i, row in enumerate(rows, 1):
        pid = (row.get("productId") or "").strip()
        iid = (row.get("itemId") or "").strip()
        vid = (row.get("vendorItemId") or "").strip()
        if not pid:
            print(f"[{i}/{len(rows)}] skip: empty productId")
            continue

        print(f"[{i}/{len(rows)}] productId={pid} itemId={iid} vendorItemId={vid}")
        try:
            resp, soup, out_path = fetch_html(pid, iid, vid, timeout=timeout, cookie=cookie, outdir=outdir)
            title = soup.title.text.strip() if soup.title else "(no title)"
            summary.append({
                "productId": pid, "itemId": iid, "vendorItemId": vid,
                "url": resp.url, "status": resp.status_code, "title": title,
                "file": str(out_path), "ok": True,
            })
            stats_ok += 1
            print(f"saved -> {out_path}")
        except Exception as e:
            print(f"failed: {e}")
            summary.append({
                "productId": pid, "itemId": iid, "vendorItemId": vid,
                "ok": False, "error": str(e),
            })

        time.sleep(random.uniform(delay_min, delay_max))

    if jsonl_path:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as f:
            for rec in summary:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"summary saved → {jsonl_path}")

    print(f"== 완료: 성공 {stats_ok} / 실패 {len(rows) - stats_ok} / 총 {len(rows)} ==")
    return 0 if stats_ok > 0 else 1

# ─────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Coupang product HTML fetcher (single & batch)")
    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument("--input", help="CSV file (columns: productId,itemId,vendorItemId) for batch mode")
    m.add_argument("--product-id", dest="product_id", help="single mode: productId")

    p.add_argument("--item-id", dest="item_id", default="", help="single mode: itemId")
    p.add_argument("--vendor-item-id", dest="vendor_item_id", default="", help="single mode: vendorItemId")
    p.add_argument("--outdir", required=True, help="Output directory for HTML files")
    p.add_argument("--jsonl", help="Summary JSONL path (batch mode)")
    p.add_argument("--cookie-file", help="Path to cookie.txt (optional)")
    p.add_argument("--timeout", type=int, default=40, help="read timeout seconds (default: 40)")
    p.add_argument("--delay-min", type=float, default=0.8, help="batch: min sleep between requests")
    p.add_argument("--delay-max", type=float, default=1.6, help="batch: max sleep between requests")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    outdir = Path(args.outdir)

    if args.input:
        exit_code = run_batch(
            Path(args.input), outdir,
            Path(args.jsonl) if args.jsonl else None,
            args.cookie_file, args.timeout, args.delay_min, args.delay_max
        )
    else:
        exit_code = run_single(
            args.product_id, args.item_id, args.vendor_item_id,
            outdir, args.cookie_file, args.timeout
        )
    raise SystemExit(exit_code)
