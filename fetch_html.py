# fetch_product_html.py
import requests
from bs4 import BeautifulSoup


def fetch_html(product_id: str, item_id: str, vendor_item_id: str, timeout: int = 60):
    """쿠팡 상품 페이지 HTML을 받아 BeautifulSoup 객체 반환"""

    # URL 구성 (마지막 숫자만 바꾸면 됨)
    url = f"https://www.coupang.com/vp/products/{product_id}"

    # 기본 쿼리스트링 구성
    params = {
        "itemId": item_id,
        "vendorItemId": vendor_item_id,
        "from": "home_C2",
        "traid": "home_C2",
        "trcid": "4750066",
    }

    # 최소 헤더
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        ),
    }

    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    print("status:", resp.status_code)
    print("url:", resp.url)

    # HTML 저장
    with open(f"response_{product_id}.html", "w", encoding="utf-8") as f:
        f.write(resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    print("title:", soup.title.text if soup.title else "(no title)")

    return resp, soup


if __name__ == "__main__":
    # ✅ 여기 3개만 바꿔서 다른 상품 요청 가능
    PRODUCT_ID = "7225189423"
    ITEM_ID = "23751564869"
    VENDOR_ITEM_ID = "90776061353"

    fetch_html(PRODUCT_ID, ITEM_ID, VENDOR_ITEM_ID)
