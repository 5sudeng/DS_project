import argparse, time, random, re
from pathlib import Path
from typing import Optional, Set, Iterable
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import socket as _s
import subprocess, shlex

'''
use example:c
    python crawl_category_urls.py \
    --category-url "https://www.coupang.com/np/categories/195266" \
    --start-page 1 --pages 30 \
    --max 1000 \
    --out urls.txt \
    --cookie-file cookie.txt
'''

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file: return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def build_headers(referer: Optional[str], cookie: Optional[str]) -> dict:
    h = {
        "user-agent": UA,
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": referer or "https://www.coupang.com/",
        "origin": "https://www.coupang.com",
        "connection": "keep-alive",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "navigate",
        "sec-fetch-dest": "document",
        "accept-encoding": "gzip, deflate, br",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
    }
    if cookie:
        h["cookie"] = cookie
    return h

def page_urls(pattern: Optional[str], base_url: Optional[str], start_page: int, pages: int) -> Iterable[str]:
    if pattern:
        for p in range(start_page, start_page + pages):
            yield pattern.format(page=p)
    else:
        sep = "&" if ("?" in (base_url or "")) else "?"
        for p in range(start_page, start_page + pages):
            yield f"{base_url}{sep}page={p}"

def fetch_html(url: str, headers: dict, retries: int = 2, connect_to=8, read_to=20) -> str:
    orig_getaddrinfo = _s.getaddrinfo
    def _ipv4_only(*a, **k):
        res = orig_getaddrinfo(*a, **k)
        return [r for r in res if r[0] == _s.AF_INET] or res
    _s.getaddrinfo = _ipv4_only

    try:
        sess = requests.Session()
        retry = Retry(
            total=retries, connect=retries, read=retries, status=retries,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        sess.mount("https://", adapter); sess.mount("http://", adapter)

        last = None
        for attempt in range(retries + 1):
            try:
                r = sess.get(url, headers=headers, timeout=(connect_to, read_to), allow_redirects=True)
                r.raise_for_status()
                return r.text
            except requests.Timeout as e:
                last = e
                delay = (2 ** attempt) * 0.7 + random.uniform(0, 0.8)
                print(f"[retry {attempt+1}/{retries}] timeout -> wait {delay:.2f}s")
                time.sleep(delay)
            except requests.RequestException as e:
                last = e
                if attempt < retries:
                    delay = (2 ** attempt) * 0.7 + random.uniform(0, 0.8)
                    print(f"[retry {attempt+1}/{retries}] error: {e} -> wait {delay:.2f}s")
                    time.sleep(delay)
                else:
                    break

        # 최종 fallback: curl (HTTP/1.1 + IPv4 + compressed)
        tmp_path = Path("_curl_cat_tmp.html").absolute()
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
            subprocess.run(curl_cmd, check=True)
        except subprocess.CalledProcessError as ce:
            print("[fallback] curl exit:", ce.returncode)
        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            return tmp_path.read_text(encoding="utf-8", errors="ignore")
        raise last or RuntimeError("request failed")
    finally:
        _s.getaddrinfo = orig_getaddrinfo

def extract_product_links(html: str, base: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: Set[str] = set()

    # 1) a[href]에서 /vp/products/{id} 패턴 찾기
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/vp/products/" in href:
            absu = urljoin(base, href)
            urls.add(absu)

    # 2) 백업: 정규식 스캔(동적 렌더링 대비)
    rx = re.compile(r"https?://www\.coupang\.com/vp/products/\d+(?:\?[^\"'<>\\s]*)?")
    for m in rx.finditer(html):
        urls.add(m.group(0))

    # 정리: 같은 productId 중복 제거(쿼리 달라도 1개로)
    normed = {}
    for u in urls:
        pu = urlparse(u)
        m = re.search(r"/vp/products/(\d+)", pu.path)
        if not m:
            continue
        pid = m.group(1)
        # 쿼리는 버려서 대표 링크로
        normed[pid] = f"https://www.coupang.com/vp/products/{pid}"
    return set(normed.values())

def main():
    ap = argparse.ArgumentParser(description="Coupang category URL crawler (collect product detail URLs)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--category-url", help="카테고리 목록 URL (예: https://www.coupang.com/np/categories/XXXX)")
    g.add_argument("--url-pattern", help="페이지 패턴 (예: 'https://www.coupang.com/np/categories/XXXX?page={page}')")

    ap.add_argument("--start-page", type=int, default=1, help="시작 페이지")
    ap.add_argument("--pages", type=int, default=200, help="가져올 페이지 수")
    ap.add_argument("--out", default="urls.txt", help="저장 파일 (한 줄당 한 URL)")
    ap.add_argument("--max", dest="max_count", type=int, default=1000, help="최대 수집 개수")
    ap.add_argument("--cookie-file", default=None, help="로그인 쿠키 파일 (선택)")

    ap.add_argument("--sleep-min", type=float, default=0.8)
    ap.add_argument("--sleep-max", type=float, default=1.6)

    args = ap.parse_args()

    cookie = load_cookie(args.cookie_file)
    base_referer = args.category_url or (args.url_pattern.format(page=args.start_page) if args.url_pattern else None)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen: Set[str] = set()
    if out_path.exists():
        # 중복 방지
        for line in out_path.read_text(encoding="utf-8").splitlines():
            seen.add(line.strip())

    with out_path.open("a", encoding="utf-8") as fp:
        total_new = 0
        for page_url in page_urls(args.url_pattern, args.category_url, args.start_page, args.pages):
            print(f"⇒ GET {page_url}")
            html = fetch_html(page_url, build_headers(page_url or base_referer, cookie), retries=2)
            urls = extract_product_links(html, base=page_url)
            new_urls = [u for u in urls if u not in seen]
            if not new_urls:
                print("  (no new urls on this page)")
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