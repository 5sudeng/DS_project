'''
use example :
    python to_schema.py \
        --html-dir outputs_html \
        --quantity-dir outputs_quantity \
        --reviews-dir outputs_reviews \
        --inquiries-dir outputs_inquiries \
        --outdir outputs_structured \
        --download-images
'''

import os, glob, re, json, argparse, hashlib, urllib.request
from bs4 import BeautifulSoup

# ---------- 기본 유틸 ----------
def norm_url(u: str) -> str:
    if not u:
        return u
    return "https:" + u if u.startswith("//") else u

def load_html(path): 
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json(path): 
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- JSON 파싱 (quantity / reviews / inquiries) ----------

def parse_quantity(qdata):
    out = {}
    first = qdata[0] if isinstance(qdata, list) and qdata else {}
    out["delivery"] = first.get("delivery", {})
    out["deliveryList"] = first.get("deliveryList", [])
    out["cashBackSummary"] = first.get("cashBackSummary", {})
    out["priceInfo"] = {}

    title, attribute_title = None, None
    options, option_images = [], []
    product_id, landing = None, {}

    for block in first.get("moduleData", []):
        vt = block.get("viewType")
        if vt == "PRODUCT_DETAIL_PRODUCT_INFO":
            title = block.get("title")
            attribute_title = block.get("attributeBasedTitle")
        if "landingProductId" in block:
            landing = {
                "productId": block.get("landingProductId"),
                "itemId": block.get("landingItemId"),
                "vendorItemId": block.get("landingVendorItemId"),
            }
            product_id = block.get("landingProductId")
            for opt in block.get("optionList", []):
                img = norm_url(opt.get("hoverImageUrl"))
                options.append({
                    "optionItemName": opt.get("optionItemName"),
                    "itemId": opt.get("itemId"),
                    "vendorItemId": opt.get("vendorItemId"),
                    "finalPrice": opt.get("finalPrice"),
                    "finalUnitPrice": opt.get("finalUnitPrice"),
                    "deliveryType": opt.get("deliveryType"),
                    "deliveryBadgeUrl": opt.get("deliveryBadgeUrl"),
                    "soldOut": opt.get("soldOut"),
                    "selected": opt.get("selected"),
                    "hoverImageUrl": img,
                    "hoverSelectionText": opt.get("hoverSelectionText"),
                })
                if img:
                    option_images.append(img)
        if vt == "PRODUCT_DETAIL_PRICE_INFO":
            out["priceInfo"] = block.get("detailPriceBundle", {}).get("finalPrice", {})

    # Expanded items (있으면)
    items_expanded = []
    for block in first.get("moduleData", []):
        if isinstance(block, dict) and "items" in block:
            for it in block.get("items", []):
                items_expanded.append({
                    "itemId": it.get("itemBasicInfo", {}).get("itemId"),
                    "itemName": it.get("itemBasicInfo", {}).get("itemName"),
                    "vendorItemId": it.get("itemBasicInfo", {}).get("vendorItemId"),
                    "finalPrice": it.get("priceInfo", {}).get("finalPrice"),
                    "finalUnitPrice": it.get("priceInfo", {}).get("finalUnitPrice"),
                    "deliveryDateDescriptions": it.get("deliveryInfo", {}).get("deliveryDateDescriptions"),
                    "finalDeliveryDescription": it.get("priceInfo", {}).get("finalDeliveryDescription"),
                    "soldOut": it.get("stockInfo", {}).get("soldOut"),
                })

    out.update({
        "title": title,
        "attributeBasedTitle": attribute_title,
        "landing": landing,
        "productId": product_id,
        "options": options,
        "optionImages": option_images,
        "optionItemsExpanded": items_expanded,
    })
    return out


def parse_inquiries(data, max_items=50):
    try:
        nav = data["success"]["rData"]["navigation"]
    except KeyError:
        return {"total": 0, "inquiries": []}
    contents = nav.get("contents", [])
    out_items = []
    for c in contents[:max_items]:
        out_items.append({
            "inquiryId": c.get("inquiryId"),
            "createdAt": c.get("createdAt"),
            "formattedCreateDate": c.get("formattedCreateDate"),
            "vendorItemId": c.get("vendorItemId"),
            "vendorId": c.get("vendorId"),
            "vendorName": c.get("vendorName"),
            "serializedAttrName": c.get("serializedAttrName"),
            "content": c.get("content"),
            "comments": [
                {
                    "inquiryCommentId": cm.get("inquiryCommentId"),
                    "displayWriter": cm.get("displayWriter"),
                    "content": cm.get("content"),
                    "createdAt": cm.get("createdAt"),
                    "formattedCreateDate": cm.get("formattedCreateDate"),
                }
                for cm in (c.get("comments") or [])
            ]
        })
    return {
        "total": data["success"]["rData"].get("totalElements"),
        "pages": data["success"]["rData"].get("navigation", {}).get("totalPageIndex"),
        "inquiries": out_items
    }


def parse_reviews(rdata, max_reviews=100):
    try:
        rD = rdata["rData"]
    except KeyError:
        return {"summary": {}, "reviews": [], "pageInfo": {}}
    summary = rD.get("ratingSummaryTotal", {})
    paging = rD.get("paging", {})
    contents = paging.get("contents", [])
    out_reviews = []
    image_urls, video_urls = [], []
    for r in contents[:max_reviews]:
        imgs = []
        for att in (r.get("attachments") or []):
            origin = att.get("imgSrcOrigin") or att.get("imgSrcThumbnail")
            if origin:
                imgs.append(origin)
                image_urls.append(origin)
        for v in (r.get("videoAttachments") or []):
            vurl = v.get("videoUrl") or v.get("videoThumbnailUrl")
            if vurl:
                video_urls.append(vurl)
        out_reviews.append({
            "reviewId": r.get("reviewId"),
            "productId": r.get("productId"),
            "vendorItemId": r.get("vendorItemId"),
            "itemId": r.get("itemId"),
            "rating": r.get("rating"),
            "title": r.get("title"),
            "content": r.get("content"),
            "reviewAt": r.get("reviewAt"),
            "displayWriter": r.get("displayWriter"),
            "displayName": r.get("displayName"),
            "attachmentsCount": len(imgs),
            "imageUrls": imgs,
        })
    return {
        "summary": summary,
        "pageInfo": {
            "page": paging.get("page"),
            "sizePerPage": paging.get("sizePerPage"),
            "totalCount": paging.get("totalCount"),
            "totalPage": paging.get("totalPage"),
        },
        "reviews": out_reviews,
        "imageUrls": image_urls,
        "videoUrls": video_urls
    }

# ---------- HTML 파싱 ----------
def parse_html_images(html_text):
    """상세설명(판매자 설명) 영역 우선 + HTML 전체에서 'retail' 이미지만 추출"""
    soup = BeautifulSoup(html_text, "html.parser")

    # 상세영역 찾기
    detail = (
        soup.find(id="productDetail")
        or soup.find("div", {"data-component": "productDetail"})
        or soup.find("div", {"class": re.compile(r"(product-)?detail", re.I)})
    )
    scope = detail if detail else soup

    def is_retail(u: str) -> bool:
        return bool(u) and ("image/retail/images/" in u)

    urls = []
    for img in scope.find_all("img"):
        src = img.get("src") or img.get("data-src")
        src = norm_url(src)
        if is_retail(src):
            urls.append(src)

    # CSS url() 패턴
    text = str(scope)
    for u in re.findall(r'url\(["\']?(//[^)"\']+)', text):
        u = norm_url(u)
        if is_retail(u):
            urls.append(u)

    # 정규식으로 HTML 전체에서 retail URL 보충
    for u in re.findall(r"""(//thumbnail[^"'\s]+image/retail/images/[^"'\s]+)""", html_text):
        u = norm_url(u)
        if is_retail(u):
            urls.append(u)

    # 중복 제거
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            uniq.append(u); seen.add(u)
    return uniq

def extract_ids_from_html(html_text):
    txt = BeautifulSoup(html_text, "html.parser").get_text(" ", strip=True)
    ids = {}
    for key in ("productId", "itemId", "vendorItemId"):
        m = re.search(rf"{key}\\s*[:=]\\s*[\"']?(\\d+)", txt)
        if m:
            ids[key] = int(m.group(1))
    return ids

def unique_image_name(url, product_id):
    md5 = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    ext = os.path.splitext(url.split("?")[0])[-1]
    if len(ext) > 5 or not ext.startswith("."):
        ext = ".jpg"
    return f"html_{product_id}_{md5}{ext}"

def download_images(urls, out_dir, product_id):
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for u in urls:
        if not u:
            continue
        fname = unique_image_name(u, product_id)
        path = os.path.join(out_dir, fname)
        try:
            urllib.request.urlretrieve(u, path)
            saved.append(path)
        except Exception as e:
            print(f"  [warn] {u} -> {e}")
    return saved

# ---------- 메인 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-dir", required=True, help="HTML 폴더 (e.g. outputs_html)")
    ap.add_argument("--quantity-dir", required=True, help="quantity 폴더")
    ap.add_argument("--reviews-dir", required=True, help="reviews 폴더")
    ap.add_argument("--inquiries-dir", required=True, help="inquiries 폴더")
    ap.add_argument("--outdir", default="out", help="저장 폴더")
    ap.add_argument("--download-images", action="store_true", help="이미지 다운로드")
    args = ap.parse_args()

    html_files = sorted(glob.glob(os.path.join(args.html_dir, "response_*.html")))
    if not html_files:
        print("no HTML files found")
        return

    print(f"총 {len(html_files)}개 HTML 처리 시작\n")

    for html_path in html_files:
        html_name = os.path.basename(html_path)
        m = re.search(r"response_(\d+)", html_name)
        if not m:
            print(f"  -> skip (no productId match): {html_name}")
            continue
        pid = m.group(1)

        print(f"▶ productId={pid}")

        # 파일 매칭
        q = glob.glob(os.path.join(args.quantity_dir, f"quantity_info_{pid}_*.json"))
        r = glob.glob(os.path.join(args.reviews_dir, f"review_{pid}_*.json"))
        i = glob.glob(os.path.join(args.inquiries_dir, f"inquiries_{pid}_*.json"))
        qpath, rpath, ipath = (q[0] if q else None, r[0] if r else None, i[0] if i else None)

        # HTML 파싱
        html_text = load_html(html_path)
        ids = extract_ids_from_html(html_text)
        html_imgs = parse_html_images(html_text)
        print(f"  → HTML retail 이미지 {len(html_imgs)}건")

        # 폴더 구성
        out_dir = os.path.join(args.outdir, pid)
        os.makedirs(out_dir, exist_ok=True)

        # Optional JSON 병합 (있을 때만)
        q_parsed = load_json(qpath) if qpath else None
        r_parsed = load_json(rpath) if rpath else None
        i_parsed = load_json(ipath) if ipath else None

        q = parse_quantity(q_parsed) if q_parsed else {}
        r = parse_reviews(r_parsed) if r_parsed else {"summary": {}, "pageInfo": {}, "reviews": []}
        i = parse_inquiries(i_parsed) if i_parsed else {"total": 0, "inquiries": []}

        product_json = {
            "productId": ids.get("productId", pid),
            "itemId": (q.get("landing") or {}).get("itemId") or ids.get("itemId"),
            "vendorItemId": (q.get("landing") or {}).get("vendorItemId") or ids.get("vendorItemId"),
            "productTitle": q.get("title") or q.get("attributeBasedTitle"),
            "brand": None,
            "delivery": q.get("delivery"),
            "price": q.get("priceInfo", {}).get("price"),
            "unitPrice": q.get("priceInfo", {}).get("unitPriceAmount"),
            "unitPriceDescription": q.get("priceInfo", {}).get("unitPriceDescription"),
            "cashBackSummary": q.get("cashBackSummary"),
            "options": q.get("options"),
            "optionsExpanded": q.get("optionItemsExpanded"),
            "images": {"fromHTML": html_imgs},
            "reviewsSummary": r.get("summary"),
            "reviewsPageInfo": r.get("pageInfo"),
            "inquiries": i.get("inquiries"),
            "inquiriesTotal": i.get("total"),
            "source": {
                "html": html_path,
                "quantity": qpath,
                "reviews": rpath,
                "inquiries": ipath,
            },
        }

        # 저장 경로
        with open(os.path.join(out_dir, f"product_{pid}.json"), "w", encoding="utf-8") as f:
            json.dump(product_json, f, ensure_ascii=False, indent=2)

        # 이미지 매니페스트 (HTML 전용)
        with open(os.path.join(out_dir, f"image_manifest_{pid}.json"), "w", encoding="utf-8") as f:
            json.dump({"productId": pid, "htmlImageUrls": html_imgs}, f, ensure_ascii=False, indent=2)

        # 리뷰 JSONL (있을 때만)
        if r.get("reviews"):
            page = r.get("pageInfo", {}).get("page", 1)
            out_reviews = os.path.join(out_dir, f"reviews_{pid}_p{page}.jsonl")
            with open(out_reviews, "w", encoding="utf-8") as f:
                for rr in r["reviews"]:
                    f.write(json.dumps(rr, ensure_ascii=False) + "\n")

        if args.download_images and html_imgs:
            img_dir = os.path.join(out_dir, "images")
            saved = download_images(html_imgs, img_dir, pid)
            print(f"  -> 다운로드 {len(saved)}건 완료")

        print(f"완료: {pid}\n")

    print("모든 HTML 처리 완료")

if __name__ == "__main__":
    main()