#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build structured, per-product JSON by merging HTML / quantity / reviews / inquiries / BTF.

This version treats BTF exactly like the other folders — no separate JSONL option.

USAGE
-----
python to_schema_plus_btf.py \
  --html-dir data/outputs_html \
  --quantity-dir data/outputs_quantity \
  --reviews-dir data/outputs_reviews \
  --inquiries-dir data/outputs_inquiries \
  --btf-dir data/outputs_btf \
  --outdir data/outputs_structured \
  --download-images

Output
------
<outdir>/<productId>/product_<productId>.json
<outdir>/<productId>/image_manifest_<productId>.json
<outdir>/<productId>/reviews_<productId>_p<page>.jsonl (if any)
<outdir>/<productId>/images/btf_<productId>_*.jpg (if --download-images)  <- BTF 이미지도 다운로드됨
"""

import os, glob, re, json, argparse, hashlib, urllib.request
from typing import Dict, Any, List, Optional, Set
from bs4 import BeautifulSoup

# ---------- 기본 유틸 ----------
def norm_url(u: str) -> str:
    if not u:
        return u
    # URL 양 끝의 공백 제거, 특히 마지막에 붙는 '\' 문자 제거
    u = u.strip().rstrip('\\')
    return "https:" + u if u.startswith("//") else u

def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- 텍스트 유틸 ----------
_ws = re.compile(r"\s+")

def norm_ws(s: str) -> str:
    return _ws.sub(" ", s).strip()

# ---------- JSON 파싱 (quantity / reviews / inquiries) ----------

def parse_quantity(qdata: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
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


def parse_inquiries(data: Any, max_items: int = 50) -> Dict[str, Any]:
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
            ],
        })
    return {
        "total": data["success"]["rData"].get("totalElements"),
        "pages": data["success"]["rData"].get("navigation", {}).get("totalPageIndex"),
        "inquiries": out_items,
    }


def parse_reviews(rdata: Any, max_reviews: int = 100) -> Dict[str, Any]:
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
        "videoUrls": video_urls,
    }

# ---------- HTML 파싱 ----------

def parse_html_images(html_text: str) -> List[str]:
    """상세설명(판매자 설명) 우선 + HTML 전체에서 'retail' 이미지만 추출"""
    soup = BeautifulSoup(html_text, "html.parser")

    detail = (
        soup.find(id="productDetail")
        or soup.find("div", {"data-component": "productDetail"})
        or soup.find("div", {"class": re.compile(r"(product-)?detail", re.I)})
    )
    scope = detail if detail else soup

    def is_retail(u: str) -> bool:
        return bool(u) and ("image/retail/images/" in u)

    urls: List[str] = []
    for img in scope.find_all("img"):
        src = img.get("src") or img.get("data-src")
        src = norm_url(src)
        if is_retail(src):
            urls.append(src)

    text = str(scope)
    for u in re.findall(r'url\(["\']?(//[^)"\']+)', text):
        u = norm_url(u)
        if is_retail(u):
            urls.append(u)

    for u in re.findall(r"""(//thumbnail[^"'\s]+image/retail/images/[^"'\s]+)""", html_text):
        u = norm_url(u)
        if is_retail(u):
            urls.append(u)

    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            uniq.append(u); seen.add(u)
    return uniq


def extract_ids_from_html(html_text: str) -> Dict[str, int]:
    txt = BeautifulSoup(html_text, "html.parser").get_text(" ", strip=True)
    ids: Dict[str, int] = {}
    for key in ("productId", "itemId", "vendorItemId"):
        m = re.search(rf"{key}\s*[:=]\s*[\"']?(\d+)", txt)
        if m:
            ids[key] = int(m.group(1))
    return ids

# ---------- BTF 파싱 ----------
# ... (중략: iter_text_leaves, collect_btf_fields)

def iter_text_leaves(obj: Any) -> List[str]:
    out: List[str] = []
    stack = [obj]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str):
            s = norm_ws(node)
            if s:
                out.append(s)
    return out


def collect_btf_fields(obj: Dict[str, Any]) -> Dict[str, str]:
    """Top-level key별 텍스트를 합쳐 반환 (필드 단위 스키마용)."""
    res: Dict[str, str] = {}
    if not isinstance(obj, dict):
        return res
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            leaf_texts = iter_text_leaves(v)
            blob = norm_ws("\n".join(leaf_texts))
            if blob:
                res[str(k)] = blob
        elif isinstance(v, str):
            s = norm_ws(v)
            if s:
                res[str(k)] = s
    return res


def parse_btf_images(obj: Dict[str, Any]) -> List[str]:
    """BTF 안에서 그럴듯한 이미지 URL 추출 (details 필드 우선 + JSON 텍스트)."""
    urls: Set[str] = set()

    # 1. details 필드에서 명시적으로 추출 (가장 확실함)
    details = obj.get("details", [])
    for detail_block in details:
        if isinstance(detail_block, dict):
            # vendorItemContentDescriptions 리스트 안에서 content 필드를 찾습니다.
            content_descriptions = detail_block.get("vendorItemContentDescriptions", [])
            for desc in content_descriptions:
                if isinstance(desc, dict) and desc.get("detailType") == "IMAGE":
                    content = desc.get("content")
                    if content:
                        urls.add(norm_url(content))

    # 2. 백업: 전체 JSON 텍스트 정규식 검색
    txts = json.dumps(obj, ensure_ascii=False)
    # retail/vendor/product 경로가 포함된 URL을 찾습니다.
    for u in re.findall(r'(//[^"\s]+image/(?:retail|vendor|product)/[^"\s]+)', txts):
        urls.add(norm_url(u))
    
    return list(urls)


def load_btf_for_pid(btf_dir: str, pid: str) -> Optional[Dict[str, Any]]:
    if not btf_dir or not os.path.isdir(btf_dir):
        return None
    patterns = [
        f"btf_{pid}_*.json",
        f"*_{pid}_btf.json",
        f"*{pid}*.json",
    ]
    cands: List[str] = []
    for pat in patterns:
        cands.extend(glob.glob(os.path.join(btf_dir, pat)))
    cands = sorted(set(cands))
    if not cands:
        return None
    try:
        obj = load_json(cands[0])
    except Exception:
        return None
    return obj.get("response", obj) if isinstance(obj, dict) else None

# ---------- 다운로드 유틸 ----------

def unique_image_name(url: str, product_id: str, prefix: str) -> str:
    """다운로드 파일명 생성. prefix로 출처(html/btf)를 구분합니다."""
    md5 = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    ext = os.path.splitext(url.split("?")[0])[-1]
    if len(ext) > 5 or not ext.startswith("."):
        ext = ".jpg" # 기본 확장자
    return f"{prefix}_{product_id}_{md5}{ext}"

def download_images(urls: List[str], out_dir: str, product_id: str, prefix: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    saved: List[str] = []
    for u_raw in urls:
        u = norm_url(u_raw)
        if not u:
            continue
        fname = unique_image_name(u, product_id, prefix)
        path = os.path.join(out_dir, fname)
        if os.path.exists(path): # 이미 다운로드된 파일은 건너뜁니다.
            saved.append(path)
            continue
        try:
            # 기본 User-Agent 설정
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            
            urllib.request.urlretrieve(u, path)
            saved.append(path)
        except Exception as e:
            print(f"  [warn] {u} ({prefix}) -> {e}")
    return saved

# ---------- 메인 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-dir", required=True, help="HTML 폴더 (e.g. outputs_html)")
    ap.add_argument("--quantity-dir", required=True, help="quantity 폴더")
    ap.add_argument("--reviews-dir", required=True, help="reviews 폴더")
    ap.add_argument("--inquiries-dir", required=True, help="inquiries 폴더")
    ap.add_argument("--btf-dir", required=True, help="BTF JSON 폴더 (e.g. outputs_btf)")
    ap.add_argument("--outdir", default="out", help="저장 폴더")
    ap.add_argument("--download-images", action="store_true", help="HTML 및 BTF 이미지 다운로드")
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
        b = load_btf_for_pid(args.btf_dir, pid)
        qpath, rpath, ipath = (q[0] if q else None, r[0] if r else None, i[0] if i else None)

        # HTML 파싱
        html_text = load_text(html_path)
        ids = extract_ids_from_html(html_text)
        html_imgs = parse_html_images(html_text)
        print(f"  → HTML retail 이미지 {len(html_imgs)}건")

        # BTF 파싱
        btf_fields: Dict[str, str] = {}
        btf_imgs: List[str] = []
        if b:
            btf_fields = collect_btf_fields(b)
            btf_imgs = parse_btf_images(b) # 수정된 함수 사용
            print(f"  → BTF fields {len(btf_fields)}개, 이미지 {len(btf_imgs)}건")
        else:
            print("  → BTF 없음 (skip)")

        # 폴더 구성
        out_dir = os.path.join(args.outdir, pid)
        os.makedirs(out_dir, exist_ok=True)

        # Optional JSON 병합 (있을 때만)
        q_parsed = load_json(qpath) if qpath else None
        r_parsed = load_json(rpath) if rpath else None
        i_parsed = load_json(ipath) if ipath else None

        qj = parse_quantity(q_parsed) if q_parsed else {}
        rj = parse_reviews(r_parsed) if r_parsed else {"summary": {}, "pageInfo": {}, "reviews": []}
        ij = parse_inquiries(i_parsed) if i_parsed else {"total": 0, "inquiries": []}

        product_json = {
            "productId": ids.get("productId", pid),
            "itemId": (qj.get("landing") or {}).get("itemId") or ids.get("itemId"),
            "vendorItemId": (qj.get("landing") or {}).get("vendorItemId") or ids.get("vendorItemId"),
            "productTitle": qj.get("title") or qj.get("attributeBasedTitle"),
            "brand": None,
            # Quantity-derived
            "delivery": qj.get("delivery"),
            "price": (qj.get("priceInfo") or {}).get("price"),
            "unitPrice": (qj.get("priceInfo") or {}).get("unitPriceAmount"),
            "unitPriceDescription": (qj.get("priceInfo") or {}).get("unitPriceDescription"),
            "cashBackSummary": qj.get("cashBackSummary"),
            "options": qj.get("options"),
            "optionsExpanded": qj.get("optionItemsExpanded"),
            # Images
            "images": {
                "fromHTML": html_imgs,
                "fromBTF": btf_imgs,
            },
            # Reviews / Inquiries
            "reviewsSummary": rj.get("summary"),
            "reviewsPageInfo": rj.get("pageInfo"),
            "inquiries": ij.get("inquiries"),
            "inquiriesTotal": ij.get("total"),
            # BTF fields (field-level schema text)
            "btfFields": btf_fields,
            # Source paths
            "source": {
                "html": html_path,
                "quantity": qpath,
                "reviews": rpath,
                "inquiries": ipath,
                "btf": os.path.join(args.btf_dir, f"*{pid}*.json"),
            },
        }

        # 저장
        with open(os.path.join(out_dir, f"product_{pid}.json"), "w", encoding="utf-8") as f:
            json.dump(product_json, f, ensure_ascii=False, indent=2)

        # 이미지 매니페스트 (HTML/BTF)
        with open(os.path.join(out_dir, f"image_manifest_{pid}.json"), "w", encoding="utf-8") as f:
            json.dump({"productId": pid, "htmlImageUrls": html_imgs, "btfImageUrls": btf_imgs}, f, ensure_ascii=False, indent=2)

        # 리뷰 JSONL (있을 때만)
        if rj.get("reviews"):
            page = (rj.get("pageInfo") or {}).get("page", 1)
            out_reviews = os.path.join(out_dir, f"reviews_{pid}_p{page}.jsonl")
            with open(out_reviews, "w", encoding="utf-8") as f:
                for rr in rj["reviews"]:
                    f.write(json.dumps(rr, ensure_ascii=False) + "\n")

        # (옵션) 이미지 다운로드
        if args.download_images:
            img_dir = os.path.join(out_dir, "images")
            
            # 1. HTML 이미지 다운로드
            saved_html = download_images(html_imgs, img_dir, pid, prefix="html")
            print(f"  -> HTML 이미지 다운로드 {len(saved_html)}건 완료")
            
            # 2. BTF 이미지 다운로드 (추가)
            saved_btf = download_images(btf_imgs, img_dir, pid, prefix="btf")
            print(f"  -> BTF 이미지 다운로드 {len(saved_btf)}건 완료")

        print(f"완료: {pid}\n")

    print("모든 HTML 처리 완료")

if __name__ == "__main__":
    main()