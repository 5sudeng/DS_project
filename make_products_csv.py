from urllib.parse import urlparse, parse_qs
import csv, sys, re, time, random
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import subprocess, shlex
import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# ─────────────────────────────────────────────────────
# Step 1) Extract IDs directly from product URLs
# ex) https://www.coupang.com/vp/products/8250433942?itemId=23751564869&vendorItemId=90776061353
# ─────────────────────────────────────────────────────

def extract_ids(url: str) -> Optional[Tuple[str, str, str]]:
    url = url.strip()
    if not url:
        return None
    pu = urlparse(url)
    # /vp/products/{productId}
    m = re.search(r"/vp/products/(\d+)", pu.path)
    if not m:
        return None
    product_id = m.group(1)
    qs = parse_qs(pu.query)
    item_id = (qs.get("itemId") or qs.get("landingItemId") or [""])[0]
    vendor_item_id = (qs.get("vendorItemId") or qs.get("landingVendorItemId") or [""])[0]
    return product_id, item_id, vendor_item_id

# ─────────────────────────────────────────────────────
# Step 2) Optional backfill: visit product page HTML to find missing IDs
#    - Uses simple GET (no browser) with short retries
#    - Supports cookie (login) to improve success rate
# ─────────────────────────────────────────────────────

def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def build_headers(referer: str, cookie: Optional[str]) -> Dict[str, str]:
    h = {
        "user-agent": UA,
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "referer": referer,
        "origin": "https://www.coupang.com",
        # light browser hints
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

def fetch_html(url: str, headers: Dict[str, str], retries: int = 2, connect_to: int = 8, read_to: int = 20) -> str:
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    import socket as _s

    # IPv4 선호 (일부 CDN IPv6 tar-pit 회피)
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
                print(f"[backfill retry {attempt+1}/{retries+1}] timeout → wait {delay:.2f}s")
                time.sleep(delay)
            except requests.RequestException as e:
                last = e
                if attempt < retries:
                    delay = (2 ** attempt) * 0.7 + random.uniform(0, 0.8)
                    print(f"[backfill retry {attempt+1}/{retries+1}] error: {e} → wait {delay:.2f}s")
                    time.sleep(delay)
                else:
                    break

        # 최종 폴백: curl (HTTP/1.1 + IPv4 + 압축)
        tmp_path = Path("_curl_backfill_tmp.html").absolute()
        curl_cmd = [
            "curl","--silent","--show-error","--location",
            "--http1.1","--ipv4","--compressed",
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

ID_PATTERNS = [
    # JSON 키들 (여러 변형)
    (re.compile(r'"landingItemId"\s*:\s*(\d+)'), "itemId"),
    (re.compile(r'"landingVendorItemId"\s*:\s*(\d+)'), "vendorItemId"),
    (re.compile(r'"itemId"\s*:\s*(\d+)'), "itemId"),
    (re.compile(r'"vendorItemId"\s*:\s*(\d+)'), "vendorItemId"),
    (re.compile(r'"itemIdList"\s*:\s*\[\s*(\d+)'), "itemId"),
    (re.compile(r'"vendorItemIdList"\s*:\s*\[\s*(\d+)'), "vendorItemId"),
    # data-* 백업
    (re.compile(r'data-item-id\s*=\s*"(\d+)"'), "itemId"),
    (re.compile(r'data-vendor-item-id\s*=\s*"(\d+)"'), "vendorItemId"),
]

def parse_missing_ids_from_html(html: str, current_item: str, current_vendor: str) -> Tuple[str, str]:
    item_id, vendor_item_id = current_item, current_vendor

    # 1차: 전체 HTML에서 바로 매치
    for rx, kind in ID_PATTERNS:
        m = rx.search(html)
        if m:
            if kind == "itemId" and not item_id:
                item_id = m.group(1)
            elif kind == "vendorItemId" and not vendor_item_id:
                vendor_item_id = m.group(1)
        if item_id and vendor_item_id:
            return item_id, vendor_item_id

    # 2차: <script>{...}</script> 블록만 따로 재검색
    for script_blob in re.findall(r"<script[^>]*>\\s*(\\{.*?\\})\\s*</script>", html, flags=re.S):
        for rx, kind in ID_PATTERNS:
            m = rx.search(script_blob)
            if m:
                if kind == "itemId" and not item_id:
                    item_id = m.group(1)
                elif kind == "vendorItemId" and not vendor_item_id:
                    vendor_item_id = m.group(1)
            if item_id and vendor_item_id:
                return item_id, vendor_item_id

    return item_id, vendor_item_id

def fill_missing_ids(rows: List[Dict[str, str]], cookie_file: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, str]]:
    cookie = load_cookie(cookie_file)
    filled = 0
    for row in rows:
        if row.get("itemId") and row.get("vendorItemId"):
            continue
        pid = row["productId"]
        url = f"https://www.coupang.com/vp/products/{pid}"
        try:
            html = fetch_html(url, build_headers(url, cookie), retries=2, connect_to=6, read_to=12)
            new_item, new_vendor = parse_missing_ids_from_html(html, row.get("itemId", ""), row.get("vendorItemId", ""))
            if new_item and not row.get("itemId"):
                row["itemId"] = new_item
            if new_vendor and not row.get("vendorItemId"):
                row["vendorItemId"] = new_vendor
            print(f"filled → {pid}: item={row.get('itemId','')}, vendor={row.get('vendorItemId','')}")
        except Exception as e:
            print(f"[fill-skip] {pid} → {e}")
        if limit and filled >= limit:
            break
        # be gentle
        time.sleep(random.uniform(0.4, 0.9))
    return rows

# ─────────────────────────────────────────────────────
# Step 3) Main: read URLs, extract IDs, optional backfill, write CSV
# ─────────────────────────────────────────────────────

def main(in_txt: str = "urls.txt", out_csv: str = "products.csv", default_size: int = 20,
         do_backfill: bool = True, cookie_file: Optional[str] = None, backfill_limit: Optional[int] = None):
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
        w = csv.DictWriter(f, fieldnames=[
            "productId", "itemId", "vendorItemId", "startPage", "pages", "size"
        ])
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows → {out_csv}")

if __name__ == "__main__":
    # Usage:
    #   python make_products_csv.py urls.txt products.csv [--no-backfill] [--cookie cookie.txt] [--size 20] [--limit 200]
    in_txt = sys.argv[1] if len(sys.argv) > 1 else "urls.txt"
    out_csv = sys.argv[2] if len(sys.argv) > 2 else "products.csv"

    # simple flag parsing (keep dependencies zero)
    args = sys.argv[3:]
    do_backfill = True
    cookie_file = None
    default_size = 20
    backfill_limit = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--no-backfill":
            do_backfill = False
            i += 1
        elif a == "--cookie" and i + 1 < len(args):
            cookie_file = args[i + 1]; i += 2
        elif a == "--size" and i + 1 < len(args):
            try:
                default_size = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif a == "--limit" and i + 1 < len(args):
            try:
                backfill_limit = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    main(in_txt, out_csv, default_size=default_size,
         do_backfill=do_backfill, cookie_file=cookie_file,
         backfill_limit=backfill_limit)