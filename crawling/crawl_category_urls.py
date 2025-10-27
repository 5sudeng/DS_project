#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""python3 crawling/crawl_category_urls.py \
    --category_url "https://www.coupang.com/np/categories/194276" \
    --pages 5 \
    --cookie_file "cookie.txt"
"""


import argparse
import random
import re
import shlex
import time
from pathlib import Path
from typing import Iterable, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



# 요청하신 User-Agent 값을 유지합니다.
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
        # 파일이 없을 경우 예외를 발생시키지 않고 None 반환하도록 수정
        print(f"cookie file not found: {cookie_file}. Proceeding without cookies.")
        return None
    return p.read_text(encoding="utf-8").strip()

def build_headers(referer: Optional[str], cookie: Optional[str]) -> dict:
    # 요청하신 헤더 값으로 업데이트했습니다.
    h = {
        "user-agent": UA,
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6,zh-CN;q=0.5,zh;q=0.4,ja;q=0.3,es;q=0.2",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        # 'referer'는 동적으로 설정하는 것이 좋지만, 기본값은 요청하신 대로 coupang.com으로 설정합니다.
        "referer": referer or "https://www.coupang.com/",
        "origin": "https://www.coupang.com",
        "connection": "keep-alive",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "navigate",
        "sec-fetch-dest": "document",
        "accept-encoding": "gzip, deflate, br, zstd",
        # 요청하신 'sec-ch-ua' 형식으로 수정 (Chromium;v="141", Not?A_Brand;v="8", Google Chrome;v="141")
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-user": "?1",  # 요청하신 헤더 추가
        # 요청하신 'cache-control' 및 'upgrade-insecure-requests' 유지
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
    }
    # 프록시 캐시 회피용 헤더는 'max-age=0'에 포함되므로 제거했습니다.
    # "pragma": "no-cache", 
    if cookie:
        h["cookie"] = cookie
    return h

class IPv4OnlyResolver:
    """일부 CDN의 IPv6 tar-pit 회피용."""
    def __enter__(self):
        import socket
        self._socket = socket
        self._orig_getaddrinfo = socket.getaddrinfo

        def _ipv4_only(*a, **k):
            res = self._orig_getaddrinfo(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res

        socket.getaddrinfo = _ipv4_only
        return self

    def __exit__(self, *exc):
        self._socket.getaddrinfo = self._orig_getaddrinfo

def make_session(retries: int) -> requests.Session:
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

def fetch_html(url: str, headers: dict, retries: int = 2, connect_to: int = 12, read_to: int = 60) -> str:
    """Requests(+재시도) 실패 시 curl(HTTP/2, IPv4, 압축) 폴백."""
    last_exc = None
    with IPv4OnlyResolver():
        sess = make_session(retries)
        for attempt in range(retries + 1):
            try:
                r = sess.get(url, headers=headers, timeout=(connect_to, read_to), allow_redirects=True)
                r.raise_for_status()
                txt = r.text
                # 간단한 차단 페이지 감지
                if ("Access Denied" in txt) or ("bot" in txt.lower() and "_abck" in txt):
                    raise requests.RequestException("Possible bot-block page returned")
                return txt
            except (requests.Timeout, requests.RequestException) as e:
                last_exc = e
                if attempt < retries:
                    delay = (2 ** attempt) * 0.9 + random.uniform(0, 0.8)
                    print(f"[retry {attempt+1}/{retries}] error: {e} -> wait {delay:.2f}s")
                    time.sleep(delay)
                else:
                    break

    # ---- curl fallback (HTTP/2) ----
    tmp_path = Path("_curl_cat_tmp.html").absolute()
    curl_cmd = [
        "curl", "--silent", "--show-error", "--location",
        "--http2",          # ← 핵심: HTTP/2 시도
        "--ipv4", "--compressed",
        "--connect-timeout", str(connect_to),
        "--max-time", str(max(read_to, connect_to + 20)),
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
        html = tmp_path.read_text(encoding="utf-8", errors="ignore")
        # 동일하게 간단한 차단 감지
        if ("Access Denied" in html) or ("bot" in html.lower() and "_abck" in html):
            raise RuntimeError("curl fallback returned suspected bot-block page (check cookie/UA)")
        return html

    raise last_exc or RuntimeError("request failed (curl fallback produced no content)")

# ─────────────────────────────────────────────────────
# Crawling helpers
# ─────────────────────────────────────────────────────
def page_urls(pattern: Optional[str], base_url: Optional[str], start_page: int, pages: int) -> Iterable[str]:
    if pattern:
        for p in range(start_page, start_page + pages):
            yield pattern.format(page=p)
        return
    # base_url이 제공되었을 때만 페이지 번호 추가 (category_url 모드)
    if base_url:
        sep = "&" if ("?" in base_url) else "?"
        for p in range(start_page, start_page + pages):
            yield f"{base_url}{sep}page={p}"

_RX_PRODUCT_FULL = re.compile(r"https?://www\.coupang\.com/vp/products/\d+(?:\?[^\"'<>\\s]*)?")
_RX_PRODUCT_ID = re.compile(r"/vp/products/(\d+)")

def extract_product_links(html: str, base: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: Set[str] = set()

    # 1) DOM에서 a[href] 스캔
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/vp/products/" in href:
            urls.add(urljoin(base, href))

    # 2) 백업: 원시 HTML 정규식 스캔
    urls.update(m.group(0) for m in _RX_PRODUCT_FULL.finditer(html))

    # 3) productId 기준으로 정규화(쿼리 제거)
    norm = {}
    for u in urls:
        m = _RX_PRODUCT_ID.search(urlparse(u).path)
        if m:
            pid = m.group(1)
            norm[pid] = f"https://www.coupang.com/vp/products/{pid}"
    return set(norm.values())

# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Coupang category URL crawler (collect product detail URLs)")
    g = ap.add_mutually_exclusive_group(required=True)
    # 요청하신 타겟 URL을 기본값으로 설정
    g.add_argument("--category_url", type=str, default="https://www.coupang.com/np/categories/194276", help="카테고리 목록 URL (예: https://www.coupang.com/np/categories/XXXX)")
    g.add_argument("--url_pattern", help="페이지 패턴 (예: 'https://www.coupang.com/np/categories/XXXX?page={page}')")

    ap.add_argument("--start_page", type=int, default=1, help="시작 페이지")
    ap.add_argument("--pages", type=int, default=2, help="가져올 페이지 수")
    ap.add_argument("--out", default="urls.txt", help="저장 파일 (한 줄당 한 URL)")
    ap.add_argument("--max", dest="max_count", type=int, default=1000, help="최대 수집 개수")
    # 요청하신 쿠키 파일명을 기본값으로 설정
    ap.add_argument("--cookie_file", default="cookie.txt", help="로그인 쿠키 파일 (선택)")
    ap.add_argument("--sleep_min", type=float, default=2.5)
    ap.add_argument("--sleep_max", type=float, default=5.6)

    args = ap.parse_args()
    cookie = load_cookie(args.cookie_file)

    # 첫 referer
    base_referer = (
        args.category_url
        or (args.url_pattern.format(page=args.start_page) if args.url_pattern else "https://www.coupang.com/")
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 기존 파일의 URL도 재사용하여 중복 방지
    seen: Set[str] = set()
    if out_path.exists():
        seen.update(line.strip() for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip())

    total_new = 0
    with out_path.open("a", encoding="utf-8") as fp:
        for page_url in page_urls(args.url_pattern, args.category_url, args.start_page, args.pages):
            print(f"⇒ GET {page_url}")
            # referer를 현재 page_url로 설정하여 headers 빌드
            current_headers = build_headers(page_url, cookie)
            html = fetch_html(page_url, current_headers, retries=2)
            urls = extract_product_links(html, base=page_url)
            new_urls = [u for u in urls if u not in seen]

            if not new_urls:
                print("  (no new urls on this page)")
            else:
                for u in new_urls:
                    fp.write(u + "\n")
                    seen.add(u)
                    total_new += 1
                    if total_new >= args.max_count:
                        print(f"== reached max_count {args.max_count}, stop ==")
                        print(f"wrote {total_new} new urls -> {out_path}")
                        return

            print(f"  (+{len(new_urls)} new) total={len(seen)}")
            time.sleep(random.uniform(args.sleep_min, args.sleep_max))

    print(f"done. total unique urls now = {len(seen)}")
    print(f"saved -> {out_path}")

if __name__ == "__main__":
    main()