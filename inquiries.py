# inquiries_fetch.py (batch-ready)
import json
import time
import csv
import argparse
import random
from pathlib import Path
from typing import Optional, Dict, Tuple, Iterable

import requests

# ── 기본값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/products/inquiries"
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
        # 약간의 XHR 지문 (과하지 않게)
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
    }
    if cookie:
        h["cookie"] = cookie
    return h


def build_params(product_id: str, page_no: int = 1, is_preview: bool = True) -> Dict[str, str]:
    return {
        "productId": product_id,
        "pageNo": str(page_no),
        "isPreview": "true" if is_preview else "false",
    }


def load_cookie(cookie_file: Optional[str]) -> Optional[str]:
    if not cookie_file:
        return None
    p = Path(cookie_file)
    if not p.is_file():
        raise FileNotFoundError(f"cookie file not found: {cookie_file}")
    return p.read_text(encoding="utf-8").strip()


def safe_request(url: str, headers: Dict[str, str], params: Dict[str, str], retries: int = 2):
    """짧은 타임아웃 + 백오프 재시도."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=(5, 10))
            return resp
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
        out = f"inquiries_{product_id}_p{page_no}_{ts}.json"
        p = save_json(data, Path(outdir), out)
        print(f"saved → {p}")

    return resp, data


# ── 배치 실행 ────────────────────────────────────────
def iter_products_from_csv(csv_path: str):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            # 기대 컬럼: productId[, itemId][, vendorItemId][, startPage][, pages]
            yield {
                "productId": (row.get("productId") or row.get("PRODUCT_ID") or "").strip(),
                "itemId": (row.get("itemId") or row.get("ITEM_ID") or "").strip(),
                "vendorItemId": (row.get("vendorItemId") or row.get("VENDOR_ITEM_ID") or "").strip(),
                "startPage": (row.get("startPage") or row.get("START_PAGE") or "1").strip(),
                "pages": (row.get("pages") or row.get("PAGES") or "1").strip(),
            }


def batch_inquiries(
    csv_path: str,
    outdir: str,
    jsonl_path: Optional[str] = None,
    cookie_file: Optional[str] = None,
    retries: int = 2,
    per_page_sleep=(1.2, 2.2),
):
    cookie = load_cookie(cookie_file)
    outdir_p = Path(outdir)
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
        if not pid:
            print(f"[{idx}/{len(rows)}] skip (missing productId)")
            fail += 1
            continue

        print(f"[{idx}/{len(rows)}] productId={pid} itemId={iid} vendorItemId={vid}")
        try:
            for p in range(start_page, start_page + pages):
                resp, data = fetch_inquiries(
                    product_id=pid,
                    page_no=p,
                    cookie=cookie,
                    item_id=iid,
                    vendor_item_id=vid,
                    outdir=outdir,
                    retries=retries,
                    single_file=True, 
                )
                if resp.status_code == 200:
                    ok += 1
                    if jsonl_fp:
                        rec = {
                            "productId": pid, "itemId": iid, "vendorItemId": vid,
                            "pageNo": p, "response": data,
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
    ap = argparse.ArgumentParser(description="Fetch product inquiries (single or batch)")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--product-id", dest="product_id", help="단일 실행: productId")
    g.add_argument("--input", dest="csv_path", help="배치 실행: CSV 파일 경로 (컬럼: productId,itemId,vendorItemId,startPage,pages)")

    ap.add_argument("--item-id", dest="item_id", help="단일 실행용 itemId", default=None)
    ap.add_argument("--vendor-item-id", dest="vendor_item_id", help="단일 실행용 vendorItemId", default=None)
    ap.add_argument("--page-no", dest="page_no", type=int, default=1, help="단일 실행 페이지 번호")
    ap.add_argument("--pages", dest="pages", type=int, default=1, help="배치: 각 상품당 몇 페이지를 가져올지 (CSV의 pages가 우선)")

    ap.add_argument("--outdir", default="outputs_inquiries", help="JSON 개별 저장 폴더")
    ap.add_argument("--jsonl", dest="jsonl_path", default=None, help="배치: 전체 응답을 JSONL로도 누적 저장")
    ap.add_argument("--cookie-file", dest="cookie_file", default=None, help="브라우저에서 복사한 cookie 문자열 파일 경로")
    ap.add_argument("--retries", type=int, default=2, help="요청 재시도 횟수")

    args = ap.parse_args()

    # 단일 실행
    if args.product_id and not args.csv_path:
        cookie = load_cookie(args.cookie_file)
        fetch_inquiries(
            product_id=args.product_id,
            page_no=args.page_no,
            cookie=cookie,
            item_id=args.item_id,
            vendor_item_id=args.vendor_item_id,
            outdir=args.outdir,
            retries=args.retries,
        )

    # 배치 실행
    elif args.csv_path:
        batch_inquiries(
            csv_path=args.csv_path,
            outdir=args.outdir,
            jsonl_path=args.jsonl_path,
            cookie_file=args.cookie_file,
            retries=args.retries,
        )
    else:
        ap.error("단일 실행(--product-id) 또는 배치(--input) 중 하나를 지정하세요.")