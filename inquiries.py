# inquiries_fetch.py
import json
import time
import requests
from typing import Optional, Dict

# ── 외부 주입할 값 ─────────────────────────────────────
PRODUCT_ID     = "8250433942"   # ← 필수
PAGE_NO        = 1              # ← 필요 시 변경
ITEM_ID        = "23751564869"  # ← referer 만들 때만 필요(없어도 OK)
VENDOR_ITEM_ID = "90776061353"  # ← referer 만들 때만 필요(없어도 OK)

COUPANG_COOKIE: Optional[str] = None  # 필요 시 브라우저에서 복사한 쿠키 문자열

# ── 고정 값 ────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/products/inquiries"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

def build_referer(product_id: str,
                  item_id: Optional[str] = None,
                  vendor_item_id: Optional[str] = None) -> str:
    """referer는 있으면 도움되고, 없어도 보통 동작. (가능하면 실제 상세 URL 권장)"""
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

def fetch_inquiries(product_id: str,
                    page_no: int = 1,
                    cookie: Optional[str] = None,
                    item_id: Optional[str] = None,
                    vendor_item_id: Optional[str] = None,
                    timeout: int = 60):
    referer = build_referer(product_id, item_id, vendor_item_id)
    headers = build_headers(referer, cookie)
    params = build_params(product_id, page_no, True)

    resp = requests.get(URL, headers=headers, params=params, timeout=timeout)
    print("status:", resp.status_code)
    print("url   :", resp.url)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    ts = int(time.time() * 1000)
    out = f"inquiries_{product_id}_p{page_no}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved → {out}")
    return resp, data

if __name__ == "__main__":
    fetch_inquiries(
        PRODUCT_ID,
        page_no=PAGE_NO,
        cookie=COUPANG_COOKIE,
        item_id=ITEM_ID,
        vendor_item_id=VENDOR_ITEM_ID,
    )
