import json
import time
import requests
import argparse, csv, random, sys, socket, subprocess, shlex
from pathlib import Path
from typing import Optional, Dict

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
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-dest": "empty",
        "connection": "keep-alive",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "x-coupang-target-market": "KR",
        "x-coupang-accept-language": "ko-KR",
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
                        timeout: int = 60,
                        outdir: Optional[str] = ".",
                        filename_prefix: str = "quantity_info"):
    referer = (
        f"https://www.coupang.com/vp/products/{product_id}"
        f"?itemId={item_id}&vendorItemId={vendor_item_id}"
    )
    headers = build_headers(referer, cookie)
    params  = build_params(product_id, item_id, vendor_item_id)

    print("[REQUEST]", URL)
    print("  referer:", referer)
    print("  params :", params)

    # 1) HTTP/2 클라이언트로 먼저 시도
    try:
        import httpx
        with httpx.Client(http2=True, headers=headers, params=params,
                          timeout=httpx.Timeout(15.0, connect=5.0, read=12.0, write=12.0),
                          follow_redirects=True) as client:
            r = client.get(URL)
            resp_status, resp_url, resp_text = r.status_code, str(r.url), r.text
            if resp_status == 200 and resp_text:
                data = r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw_text": resp_text}
                print("[httpx/h2] status:", resp_status)
                print("[httpx/h2] url   :", resp_url)
            else:
                raise RuntimeError(f"httpx/h2 unexpected status {resp_status}")
    except Exception as e_h2:
        print("[httpx/h2] failed:", e_h2)
        # 2) requests (IPv4 + 짧은 타임아웃 + 재시도)
        import socket as _s
        orig_getaddrinfo = _s.getaddrinfo
        def _ipv4_only(*a, **k):
            res = orig_getaddrinfo(*a, **k)
            return [r for r in res if r[0] == _s.AF_INET] or res
        _s.getaddrinfo = _ipv4_only
        try:
            last_err = None
            for attempt in range(1, 4):
                try:
                    r2 = requests.get(URL, headers=headers, params=params, timeout=(5, 10))
                    resp_status, resp_url, resp_text = r2.status_code, r2.url, r2.text
                    if resp_status == 200 and resp_text:
                        data = r2.json() if "application/json" in r2.headers.get("content-type","") else {"raw_text": resp_text}
                        print("[requests] status:", resp_status)
                        print("[requests] url   :", resp_url)
                        break
                    else:
                        raise RuntimeError(f"requests unexpected status {resp_status}")
                except requests.Timeout as e:
                    last_err = e
                    delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
                    print(f"[requests retry {attempt}/3] timeout -> wait {delay:.2f}s")
                    time.sleep(delay)
                except requests.RequestException as e:
                    last_err = e
                    print(f"[requests retry {attempt}/3] error:", e)
                    time.sleep(1.0)
            else:
                # 3) curl (HTTP/1.1 + ipv4 + compressed), 실패해도 파일 있으면 읽기
                from urllib.parse import urlencode
                full_url = URL + "?" + urlencode(params)
                out_tmp = Path(outdir or ".") / "_curl_quantity_tmp.json"
                curl_cmd = [
                    "curl","--silent","--show-error","--location",
                    "--http1.1","--ipv4","--compressed",
                    "--connect-timeout","5","--max-time","25",
                    "-H", f"accept: {headers['accept']}",
                    "-H", f"accept-language: {headers['accept-language']}",
                    "-H", f"user-agent: {headers['user-agent']}",
                    "-H", f"referer: {headers['referer']}",
                    "-H", "origin: https://www.coupang.com",
                    "-H", f"x-requested-with: {headers['x-requested-with']}",
                    "-H", f"sec-fetch-mode: {headers['sec-fetch-mode']}",
                    "-H", f"sec-fetch-site: {headers['sec-fetch-site']}",
                    "-H", f"sec-fetch-dest: {headers['sec-fetch-dest']}",
                    "-H", f"sec-ch-ua: {headers['sec-ch-ua']}",
                    "-H", f"sec-ch-ua-platform: {headers['sec-ch-ua-platform']}",
                    "-H", f"sec-ch-ua-mobile: {headers['sec-ch-ua-mobile']}",
                    "-H", "te: trailers",
                    "-H", "accept-encoding: gzip, deflate, br",
                    "-H", "x-coupang-target-market: KR",
                    "-H", "x-coupang-accept-language: ko-KR",
                ]
                if "cookie" in headers:
                    curl_cmd += ["-H", f"cookie: {headers['cookie']}"]
                curl_cmd += [full_url, "-o", str(out_tmp)]
                print("[fallback] curl:", " ".join(shlex.quote(c) for c in curl_cmd))
                try:
                    subprocess.run(curl_cmd, check=True)
                except subprocess.CalledProcessError as ce:
                    print("[fallback] curl non-zero exit:", ce.returncode)
                if out_tmp.exists() and out_tmp.stat().st_size > 0:
                    try:
                        data = json.loads(out_tmp.read_text(encoding="utf-8", errors="ignore"))
                    except Exception:
                        data = {"raw_text": out_tmp.read_text(encoding="utf-8", errors="ignore")}
                    resp_status, resp_url = 200, full_url
                    print("[fallback] curl read from file")
                else:
                    raise last_err or RuntimeError("curl fallback failed and no output")
        finally:
            _s.getaddrinfo = orig_getaddrinfo
        
        # synthesize a minimal response-like object for downstream code
        class _Resp: pass
        resp = _Resp()
        resp.status_code = resp_status
        resp.url = resp_url

        # 저장 경로
        ts = int(time.time() * 1000)
        out_dir = Path(outdir or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{filename_prefix}_{product_id}_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"saved → {out}")
        return resp, data

def _read_cookie_text(cookie: Optional[str], cookie_file: Optional[str]) -> Optional[str]:
    if cookie and cookie.strip():
        return cookie
    if cookie_file:
        p = Path(cookie_file)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    return None

def load_products(path: Path):
    """
    CSV: header에 productId,itemId,vendorItemId (대소문자 무관)
    JSONL: 각 라인에 같은 키들
    """
    items = []
    ext = path.suffix.lower()
    if ext == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                pid = (row.get("productId") or row.get("productid") or "").strip()
                iid = (row.get("itemId") or row.get("itemid") or "").strip()
                vid = (row.get("vendorItemId") or row.get("vendoritemid") or "").strip()
                if pid and iid and vid:
                    items.append((pid, iid, vid))
    elif ext in (".jsonl", ".ndjson"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                pid = str(obj.get("productId", "")).strip()
                iid = str(obj.get("itemId", "")).strip()
                vid = str(obj.get("vendorItemId", "")).strip()
                if pid and iid and vid:
                    items.append((pid, iid, vid))
    else:
        raise ValueError("CSV 또는 JSONL 사용")
    return items

def batch_quantity(input_items,
                   cookie: Optional[str],
                   outdir: str,
                   jsonl_summary: Optional[str] = None,
                   sleep_min: float = 1.5,
                   sleep_max: float = 3.0,
                   max_retries: int = 2):

    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_fp = None
    if jsonl_summary:
        jsonl_fp = Path(jsonl_summary).open("a", encoding="utf-8")

    total = len(input_items)
    ok, fail = 0, 0

    for idx, (pid, iid, vid) in enumerate(input_items, 1):
        print(f"\n[{idx}/{total}] productId={pid} itemId={iid} vendorItemId={vid}")
        attempt = 0
        while True:
            try:
                resp, data = fetch_quantity_info(
                    pid, iid, vid,
                    cookie=cookie,
                    timeout=60,
                    outdir=outdir,
                    filename_prefix="quantity_info"
                )

                if resp.status_code == 200 :# and isinstance(data, dict):
                    ok += 1
                    if jsonl_fp:
                        rec = {"productId": pid, "itemId": iid, "vendorItemId": vid, "response": data}
                        jsonl_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    break
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}")
            except Exception as e:
                attempt += 1
                if attempt > max_retries:
                    fail += 1
                    print(f"실패 (retries exhausted): {e}")
                    break

                delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
                print(f"재시도 {attempt}/{max_retries}... {delay:.2f}s 대기 ({e})")
                time.sleep(delay)

        time.sleep(random.uniform(sleep_min, sleep_max))

    if jsonl_fp:
        jsonl_fp.close()

    print(f"\n== 완료: 성공 {ok} / 실패 {fail} / 총 {total} ==")

    if fail:
        sys.exit(2)

def quick_probe(product_id, item_id, vendor_item_id, cookie=None):
    referer = f"https://www.coupang.com/vp/products/{product_id}?itemId={item_id}&vendorItemId={vendor_item_id}"
    headers = build_headers(referer, cookie)
    params  = build_params(product_id, item_id, vendor_item_id)
    print("[PROBE] HEAD 5/5 no-redirects")
    try:
        r = requests.head(URL, headers=headers, params=params, timeout=(5,5), allow_redirects=False)
        print("  status:", r.status_code)
    except Exception as e:
        print("  HEAD error:", e)
    print("[PROBE] GET 5/8 short")
    try:
        r = requests.get(URL, headers=headers, params=params, timeout=(5,8))
        print("  status:", r.status_code, "len:", len(r.content))
    except Exception as e:
        print("  GET error:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coupang quantity-info fetcher (single/batch)")
    parser.add_argument("--product-id", dest="product_id", help="단일 실행: productId")
    parser.add_argument("--item-id", dest="item_id", help="단일 실행: itemId")
    parser.add_argument("--vendor-item-id", dest="vendor_item_id", help="단일 실행: vendorItemId")

    parser.add_argument("--input", "-i", help="배치 실행 입력 파일 (CSV 또는 JSONL)")
    parser.add_argument("--outdir", "-o", default="outputs_quantity", help="응답 JSON 저장 경로")
    parser.add_argument("--jsonl", help="요약 JSONL 출력")
    parser.add_argument("--cookie", help="쿠키 문자열")
    parser.add_argument("--cookie-file", help="쿠키 텍스트 파일 경로")

    parser.add_argument("--sleep-min", type=float, default=1.5, help="요청 사이 최소 대기(초)")
    parser.add_argument("--sleep-max", type=float, default=3.0, help="요청 사이 최대 대기(초)")
    parser.add_argument("--retries", type=int, default=2, help="실패 시 재시도 횟수")

    args = parser.parse_args()
    cookie = _read_cookie_text(args.cookie, args.cookie_file)

    # 배치 모드
    if args.input:
        items = load_products(Path(args.input))
        if not items:
            sys.exit(1)
        batch_quantity(
            items,
            cookie=cookie,
            outdir=args.outdir,
            jsonl_summary=args.jsonl,
            sleep_min=args.sleep_min,
            sleep_max=args.sleep_max,
            max_retries=args.retries,
        )
    # 단일 모드 
    else:
        if not (args.product_id and args.item_id and args.vendor_item_id):
            sys.exit(1)
        fetch_quantity_info(
            args.product_id,
            args.item_id,
            args.vendor_item_id,
            cookie=cookie,
            timeout=60,
            outdir=args.outdir,
        )