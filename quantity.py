# quantity_info_fetch.py
import json
import time
import requests
from typing import Optional, Dict

# ── 외부 주입 ───────────────────────────────────────────────
PRODUCT_ID     = "8250433942"
ITEM_ID        = "23751564869"
VENDOR_ITEM_ID = "90776061353"
COUPANG_COOKIE: Optional[str] = None  # 브라우저에서 복사한 쿠키 (필요 시만)

# ── 고정 값 ─────────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/products/quantity-info"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

def build_headers(referer: str, cookie: Optional[str] = None) -> Dict[str, str]:
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": UA,
        "referer": referer,
        "origin": "https://www.coupang.com",
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

def fetch_quantity_info(product_id: str,
                        item_id: str,
                        vendor_item_id: str,
                        cookie: Optional[str] = None,
                        timeout: int = 60):
    referer = (
        f"https://www.coupang.com/vp/products/{product_id}"
        f"?itemId={item_id}&vendorItemId={vendor_item_id}"
    )
    headers = build_headers(referer, cookie)
    params  = build_params(product_id, item_id, vendor_item_id)

    print("[REQUEST]", URL)
    resp = requests.get(URL, headers=headers, params=params, timeout=timeout)
    print("status:", resp.status_code)
    print("url   :", resp.url)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}
        print("⚠️ JSON 파싱 실패, 원문 저장")

    ts = int(time.time() * 1000)
    out = f"quantity_info_{product_id}_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved → {out}")
    return resp, data

# ── 실행 ───────────────────────────────────────────────────
if __name__ == "__main__":
    fetch_quantity_info(
        PRODUCT_ID,
        ITEM_ID,
        VENDOR_ITEM_ID,
        cookie=COUPANG_COOKIE,
    )
