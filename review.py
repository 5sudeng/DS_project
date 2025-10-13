# review_fetch.py
import json
import time
import requests

# ─────────────────────────────────────────────────────────
# 1) 필수 값들 (상품 URL/Referer에 들어가는 파라미터)
# ─────────────────────────────────────────────────────────
PRODUCT_ID     = "7225189423"
ITEM_ID        = "23751564869"
VENDOR_ITEM_ID = "90776061353"

# 쿠키는 브라우저에서 복사한 값을 붙여 넣으세요 (필요 시)
COUPANG_COOKIE = (
    "PCID=17463420738828750192085; MARKETID=17463420738828750192085; "
    "_fbp=fb.1.1746342076379.322486828382719822; delivery_toggle=false; "
    "x-coupang-target-market=KR; x-coupang-accept-language=ko-KR; sid=917ba3097bf140eea38ef600e15484476998aff3;"
)

# 정확한 상품 상세 URL (Referer로 사용)
PRODUCT_DETAIL_URL = (
    f"https://www.coupang.com/vp/products/{PRODUCT_ID}"
    f"?itemId={ITEM_ID}&vendorItemId={VENDOR_ITEM_ID}"
)

# ─────────────────────────────────────────────────────────
# 2) 요청 대상 (리뷰 API)
#    ※ 네트워크 탭에서 확인한 'next-api/review' 엔드포인트
# ─────────────────────────────────────────────────────────
URL = "https://www.coupang.com/next-api/review"

# 리뷰 API용 파라미터 (사용 케이스에 맞게 필요값만 전달)
# 여기서는 질문에 주신 quantity-info 예시 파라미터 형태를 그대로 맞춰 둠
params = {
    "productId": PRODUCT_ID,            # 8250433942 같은 내부 productId가 필요한 경우 정확히 교체
    "vendorItemId": VENDOR_ITEM_ID,
    "deliveryToggle": "false",
    "landingItemId": ITEM_ID,
    "landingProductId": PRODUCT_ID,     # ← 실제로는 내부 productId일 수 있음(네트워크 탭 값으로 교체 권장)
    "landingVendorItemId": VENDOR_ITEM_ID,
}

# ─────────────────────────────────────────────────────────
# 3) 최소 헤더 (JSON + Referer + Origin + UA + Cookie)
# ─────────────────────────────────────────────────────────
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
    "referer": PRODUCT_DETAIL_URL,
    "origin": "https://www.coupang.com",
    "cookie": COUPANG_COOKIE,  # 쿠키가 필요 없는 환경이면 이 줄을 제거해도 됨
}

# ─────────────────────────────────────────────────────────
# 4) 요청 & 저장
# ─────────────────────────────────────────────────────────
def fetch_json(url: str, headers: dict, params: dict, timeout: int = 60):
    print("[REQUEST]", url)
    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    print("status:", resp.status_code)
    print("url:", resp.url)

    # JSON 파싱
    try:
        data = resp.json()
    except Exception:
        print("⚠️ JSON 파싱 실패 → 원문을 저장합니다.")
        data = {"raw_text": resp.text}

    # 결과 샘플 출력
    text_preview = resp.text[:300].replace("\n", " ")
    print("preview:", text_preview)

    # 파일로 저장
    ts = int(time.time())
    out = f"review_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved → {out}")

    return resp, data

if __name__ == "__main__":
    fetch_json(URL, headers, params)
