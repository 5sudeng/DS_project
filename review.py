import json
import time
import csv
import argparse
import random
from pathlib import Path
from typing import Optional, Dict, Tuple, Iterable

import requests

'''
use example (single) :
    python review.py \
        --product-id 8250433942 \
        --item-id 23751564869 \
        --vendor-item-id 90776061353 \
        --page 1 --size 30 \
        --outdir outputs_reviews \
        --cookie-file cookie.txt

use example (batch) :
    python review.py \
    --input products.csv \
    --outdir outputs_reviews \
    --jsonl outputs_reviews/reviews.jsonl \
    --cookie-file cookie.txt

'''

# ── 기본값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/review"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

# ── 유틸 ─────────────────────────────────────────────
def build_referer(product_id: str,
                  item_id: Optional[str] = None,
                  vendor_item_id: Optional[str] = None) -> str:
    base = f"https://www.coupang.com/vp/products/{product_id}"
    if item_id and vendor_item_id:
        return f"{base}?itemId={item_id}&vendorItemId={vendor_item_id}"
    return base

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
        # client hints
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        # coupang hints
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
    # 리뷰 API는 보통 page/size 필수
    params = {
        "productId": product_id,
        "page": str(page),
        "size": str(size),
    }
    if vendor_item_id:
        params["vendorItemId"] = vendor_item_id
    # 일부 케이스는 landing*을 기대 -> 있으면 넣기
    if item_id:
        params.update({
            "landingItemId": item_id,
            "landingProductId": product_id,
        })
    if vendor_item_id:
        params["landingVendorItemId"] = vendor_item_id
    return params

def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()

def safe_request(url: str, headers: Dict[str, str], params: Dict[str, str], retries: int = 2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            return requests.get(url, headers=headers, params=params, timeout=(5, 12))
        except requests.Timeout as e:
            last_err = e
            delay = (2 ** attempt) * 0.8 + random.uniform(0, 0.6)
            print(f"[retry {attempt+1}/{retries}] timeout → wait {delay:.2f}s")
            time.sleep(delay)
        except requests.RequestException as e:
            last_err = e
            print(f"[retry {attempt+1}/{retries}] error: {e}")
            time.sleep(1.0)
    raise last_err or RuntimeError("request failed")

def save_json(obj, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return out_path

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

    print("[REQUEST]", URL)
    print("  referer:", referer)
    print("  params :", params)

    resp = safe_request(URL, headers, params, retries=retries)
    print("status:", resp.status_code)
    print("url   :", resp.url)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    if outdir:
        ts = int(time.time() * 1000)
        out = f"review_{product_id}_p{page}_{ts}.json"
        p = save_json(data, Path(outdir), out)
        print(f"saved → {p}")

    return resp, data

# ── 배치 실행 ────────────────────────────────────────
def iter_products_from_csv(csv_path: str):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            # 기대: productId[, itemId][, vendorItemId][, startPage][, pages][, size]
            yield {
                "productId": (row.get("productId") or row.get("PRODUCT_ID") or "").strip(),
                "itemId": (row.get("itemId") or row.get("ITEM_ID") or "").strip(),
                "vendorItemId": (row.get("vendorItemId") or row.get("VENDOR_ITEM_ID") or "").strip(),
                "startPage": (row.get("startPage") or row.get("START_PAGE") or "1").strip(),
                "pages": (row.get("pages") or row.get("PAGES") or "1").strip(),
                "size": (row.get("size") or row.get("SIZE") or "10").strip(),
            }

def batch_reviews(
    csv_path: str,
    outdir: str,
    jsonl_path: Optional[str] = None,
    cookie_file: Optional[str] = None,
    retries: int = 2,
    per_page_sleep: Tuple[float, float] = (1.2, 2.2),
):
    cookie = load_cookie(cookie_file)
    jsonl_fp = open(jsonl_path, "a", encoding="utf-8") if jsonl_path else None

    ok = 0
    fail = 0
    rows = list(iter_products_from_csv(csv_path))

    for idx, row in enumerate(rows, 1):
        pid = row["productId"]
        iid = row.get("itemId") or None
        vid = row.get("vendorItemId") or None
        start_page = int(row.get("startPage") or 1)
        pages = int(row.get("pages") or 1)
        size = int(row.get("size") or 10)
        if not pid:
            print(f"[{idx}/{len(rows)}] skip (missing productId)")
            fail += 1
            continue

        print(f"[{idx}/{len(rows)}] productId={pid} itemId={iid} vendorItemId={vid}")
        try:
            for p in range(start_page, start_page + pages):
                resp, data = fetch_reviews(
                    product_id=pid,
                    vendor_item_id=vid,
                    item_id=iid,
                    cookie=cookie,
                    page=p,
                    size=size,
                    outdir=outdir,
                    retries=retries,
                )
                if resp.status_code == 200:
                    ok += 1
                    if jsonl_fp:
                        rec = {
                            "productId": pid, "itemId": iid, "vendorItemId": vid,
                            "page": p, "size": size, "response": data,
                        }
                        jsonl_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                time.sleep(random.uniform(*per_page_sleep))
        except Exception as e:
            print("실패:", e)
            fail += 1

    if jsonl_fp:
        jsonl_fp.close()
    total = len(rows)
    print(f"\n== 완료: 성공 {ok} / 실패 {fail} / 총 {total} ==")

# ── CLI ─────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch product reviews (single or batch)")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--product-id", dest="product_id", help="단일 실행: productId")
    g.add_argument("--input", dest="csv_path", help="배치 실행: CSV 파일 경로 (컬럼: productId,itemId,vendorItemId,startPage,pages,size)")

    ap.add_argument("--item-id", dest="item_id", default=None)
    ap.add_argument("--vendor-item-id", dest="vendor_item_id", default=None)
    ap.add_argument("--page", dest="page", type=int, default=1)
    ap.add_argument("--size", dest="size", type=int, default=10)

    ap.add_argument("--outdir", default="outputs_reviews")
    ap.add_argument("--jsonl", dest="jsonl_path", default=None)
    ap.add_argument("--cookie-file", dest="cookie_file", default=None)
    ap.add_argument("--retries", type=int, default=2)

    args = ap.parse_args()

    if args.product_id and not args.csv_path:
        cookie = load_cookie(args.cookie_file)
        fetch_reviews(
            product_id=args.product_id,
            vendor_item_id=args.vendor_item_id,
            item_id=args.item_id,
            cookie=cookie,
            page=args.page,
            size=args.size,
            outdir=args.outdir,
            retries=args.retries,
        )
    elif args.csv_path:
        batch_reviews(
            csv_path=args.csv_path,
            outdir=args.outdir,
            jsonl_path=args.jsonl_path,
            cookie_file=args.cookie_file,
            retries=args.retries,
        )
    else:
        ap.error("단일 실행(--product-id) 또는 배치(--input) 중 하나를 지정.")