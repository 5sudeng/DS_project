import time
import random
import socket
import subprocess, shlex
import csv, json
import argparse
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup


UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


def fetch_html(
    product_id: str,
    item_id: str,
    vendor_item_id: str,
    timeout: int = 40,
    cookie: Optional[str] = None,
    outdir: Optional[Path] = None,
) -> Tuple[object, BeautifulSoup, Path]:
    """
    Fetch Coupang product HTML with conservative defaults (timeouts, retries, IPv4 workaround).

    Returns (response_like, BeautifulSoup, saved_path).
    response_like has attributes (status_code, url, text).
    Always saves raw HTML to <outdir or CWD>/response_<product_id>.html
    """
    base_url = f"https://www.coupang.com/vp/products/{product_id}"

    # Try multiple URL variants (some SKUs stall unless opened without params first)
    params_full = {"itemId": item_id, "vendorItemId": vendor_item_id}
    candidates = [
        (base_url, None),                    # 1) no params
        (base_url, params_full),             # 2) with item/vendor
        (base_url, {"pageSize": "1"}),       # 3) small page variant
    ]

    # Headers (browser-like)
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept-encoding": "gzip, deflate, br",
        "user-agent": UA,
        "origin": "https://www.coupang.com",
        "referer": f"{base_url}?itemId={item_id}&vendorItemId={vendor_item_id}",
        "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
        "sec-ch-ua-platform": '"macOS"',
        "sec-ch-ua-mobile": "?0",
        "connection": "keep-alive",
    }
    if cookie:
        headers["cookie"] = cookie

    def log_request(u, p):
        print("⇒ GET", u)
        if p:
            print("   params:", p)

    # Force IPv4 DNS during requests paths to avoid IPv6 tar-pits
    orig_getaddrinfo = socket.getaddrinfo

    def _ipv4_only(*args, **kwargs):
        res = orig_getaddrinfo(*args, **kwargs)
        return [r for r in res if r[0] == socket.AF_INET] or res

    socket.getaddrinfo = _ipv4_only

    try:
        last_err = None
        resp_status = None
        resp_url = None
        resp_text = None

        # ───────────────────────────────────────────────
        # Attempt A: httpx (HTTP/2 if h2 is present), else HTTP/1.1
        # ───────────────────────────────────────────────
        try:
            import httpx  # optional
            try:
                import h2  # type: ignore
                use_http2 = True
            except Exception:
                use_http2 = False

            for u, p in candidates:
                log_request(u, p)
                try:
                    timeout_cfg = httpx.Timeout(
                        timeout=float(timeout),   # default for all
                        connect=5.0,
                        read=float(timeout),
                        write=float(timeout),
                        pool=5.0,
                    )
                    with httpx.Client(
                        http2=use_http2,
                        headers=headers,
                        timeout=timeout_cfg,
                        follow_redirects=True,
                    ) as client:
                        r = client.get(u, params=p)
                        if r.status_code == 200 and r.text:
                            resp_status, resp_url, resp_text = r.status_code, str(r.url), r.text
                            print(f"[httpx/{'h2' if use_http2 else 'h1'}] status:", resp_status)
                            print(f"[httpx/{'h2' if use_http2 else 'h1'}] url   :", resp_url)
                            break
                        else:
                            raise RuntimeError(f"httpx unexpected status {r.status_code}")
                except Exception as e:
                    last_err = e
                    print("[httpx] failed:", e)
                    time.sleep(0.4 + random.uniform(0, 0.4))
            # success? -> resp_text set
        except Exception:
            # httpx not installed or import failed → skip
            pass

        # ───────────────────────────────────────────────
        # Attempt B: requests Session + Retry (IPv4)
        # ───────────────────────────────────────────────
        if resp_text is None:
            from urllib3.util.retry import Retry
            from requests.adapters import HTTPAdapter

            sess = requests.Session()
            retry = Retry(
                total=2,
                connect=2,
                read=2,
                status=2,
                backoff_factor=0.8,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
            sess.mount("https://", adapter)
            sess.mount("http://", adapter)

            for u, p in candidates:
                log_request(u, p)
                for attempt in range(1, 3):  # keep this short so we reach curl fallback sooner if stuck
                    try:
                        r2 = sess.get(u, headers=headers, params=p, timeout=(5, timeout), allow_redirects=True)
                        if r2.status_code == 200 and r2.text:
                            resp_status, resp_url, resp_text = r2.status_code, r2.url, r2.text
                            print("[requests] status:", resp_status)
                            print("[requests] url   :", resp_url)
                            break
                        else:
                            raise RuntimeError(f"HTTP {r2.status_code}")
                    except requests.Timeout as e:
                        last_err = e
                        delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
                        print(f"[retry {attempt}/2] timeout, wait {delay:.2f}s")
                        time.sleep(delay)
                    except requests.RequestException as e:
                        last_err = e
                        print(f"[retry {attempt}/2] request error: {e}")
                        time.sleep(1.0)
                if resp_text:
                    break

        # ───────────────────────────────────────────────
        # Attempt C: curl fallback (HTTP/1.1 + IPv4 + compressed)
        # ───────────────────────────────────────────────
        if resp_text is None:
            tmp_path = Path(f"_curl_html_{product_id}.html").absolute()

            for u, p in candidates:
                qs = ("?" + urlencode(p)) if p else ""
                full_url = u + qs
                curl_cmd = [
                    "curl",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--http1.1",
                    "--ipv4",
                    "--compressed",
                    "--connect-timeout",
                    "5",
                    "--max-time",
                    str(max(15, int(timeout))),
                    "-H",
                    f"accept: {headers['accept']}",
                    "-H",
                    f"accept-language: {headers['accept-language']}",
                    "-H",
                    f"accept-encoding: {headers['accept-encoding']}",
                    "-H",
                    f"user-agent: {headers['user-agent']}",
                    "-H",
                    f"origin: {headers['origin']}",
                    "-H",
                    f"referer: {headers['referer']}",
                    "-H",
                    f"sec-ch-ua: {headers['sec-ch-ua']}",
                    "-H",
                    f"sec-ch-ua-platform: {headers['sec-ch-ua-platform']}",
                    "-H",
                    f"sec-ch-ua-mobile: {headers['sec-ch-ua-mobile']}",
                    "-H",
                    "connection: keep-alive",
                    full_url,
                    "-o",
                    str(tmp_path),
                ]
                if cookie:
                    curl_cmd.insert(-2, "-H")
                    curl_cmd.insert(-2, f"cookie: {cookie}")

                print("[fallback] curl:", " ".join(shlex.quote(c) for c in curl_cmd))
                try:
                    subprocess.run(curl_cmd, check=True)
                except subprocess.CalledProcessError as ce:
                    print("[fallback] curl exit:", ce.returncode)

                if tmp_path.exists() and tmp_path.stat().st_size > 0:
                    resp_status, resp_url = 200, full_url
                    resp_text = tmp_path.read_text(encoding="utf-8", errors="ignore")
                    print("[fallback] curl read from file")
                    break

        if resp_text is None:
            raise last_err or RuntimeError("failed to fetch html")

        # Save & parse
        save_dir = outdir if outdir else Path.cwd()
        save_dir.mkdir(parents=True, exist_ok=True)
        out_path = save_dir / f"response_{product_id}.html"
        out_path.write_text(resp_text, encoding="utf-8")
        print("status:", resp_status)
        print("url   :", resp_url)
        print("len   :", len(resp_text))
        print("saved →", out_path)

        soup = BeautifulSoup(resp_text, "html.parser")
        title = soup.title.text.strip() if soup.title else "(no title)"
        print("title:", title)

        resp_like = SimpleNamespace(status_code=resp_status, url=resp_url, text=resp_text)
        return resp_like, soup, out_path

    finally:
        socket.getaddrinfo = orig_getaddrinfo


# ───────────────────────────────────────────────
# Runners: single & batch
# ───────────────────────────────────────────────

def run_single(
    product_id: str,
    item_id: str,
    vendor_item_id: str,
    outdir: Path,
    cookie_file: Optional[str],
    timeout: int,
) -> int:
    cookie = None
    if cookie_file and Path(cookie_file).is_file():
        cookie = Path(cookie_file).read_text(encoding="utf-8").strip()
        print(f"-> Using cookie from {cookie_file}")
    resp, soup, out_path = fetch_html(
        product_id,
        item_id,
        vendor_item_id,
        timeout=timeout,
        cookie=cookie,
        outdir=outdir,
    )
    print(f"saved -> {out_path}")
    return 0


def run_batch(
    input_csv: Path,
    outdir: Path,
    jsonl_path: Optional[Path],
    cookie_file: Optional[str],
    timeout: int,
    delay_min: float,
    delay_max: float,
) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    cookie = None
    if cookie_file and Path(cookie_file).is_file():
        cookie = Path(cookie_file).read_text(encoding="utf-8").strip()
        print(f"-> Using cookie from {cookie_file}")

    # load rows
    rows = []
    with input_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"== 총 {len(rows)}개 상품 처리 ==")
    stats_ok = 0
    summary = []

    for i, row in enumerate(rows, 1):
        pid = (row.get("productId") or "").strip()
        iid = (row.get("itemId") or "").strip()
        vid = (row.get("vendorItemId") or "").strip()
        if not pid:
            print(f"[{i}/{len(rows)}] skip: empty productId")
            continue
        print(f"[{i}/{len(rows)}] productId={pid} itemId={iid} vendorItemId={vid}")
        try:
            resp, soup, out_path = fetch_html(
                pid, iid, vid, timeout=timeout, cookie=cookie, outdir=outdir
            )
            title = soup.title.text.strip() if soup.title else "(no title)"
            summary.append(
                {
                    "productId": pid,
                    "itemId": iid,
                    "vendorItemId": vid,
                    "url": resp.url,
                    "status": resp.status_code,
                    "title": title,
                    "file": str(out_path),
                    "ok": True,
                }
            )
            stats_ok += 1
            print(f"saved -> {out_path}")
        except Exception as e:
            print(f"failed: {e}")
            summary.append(
                {
                    "productId": pid,
                    "itemId": iid,
                    "vendorItemId": vid,
                    "ok": False,
                    "error": str(e),
                }
            )
        time.sleep(random.uniform(delay_min, delay_max))

    # write summary
    if jsonl_path:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as f:
            for rec in summary:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"summary saved → {jsonl_path}")

    print(f"== 완료: 성공 {stats_ok} / 실패 {len(rows) - stats_ok} / 총 {len(rows)} ==")
    return 0 if stats_ok > 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Coupang product HTML fetcher (single & batch)"
    )
    # Mode selection: either CSV input (batch) or single IDs
    parser.add_argument(
        "--input",
        help="CSV file (columns: productId,itemId,vendorItemId) for batch mode",
    )
    parser.add_argument("--product-id", dest="product_id", help="single mode: productId")
    parser.add_argument("--item-id", dest="item_id", help="single mode: itemId", default="")
    parser.add_argument(
        "--vendor-item-id", dest="vendor_item_id", help="single mode: vendorItemId", default=""
    )

    parser.add_argument("--outdir", required=True, help="Output directory for HTML files")
    parser.add_argument("--jsonl", help="Summary JSONL path (batch mode)")
    parser.add_argument("--cookie-file", help="Path to cookie.txt (optional)")
    parser.add_argument("--timeout", type=int, default=40, help="read timeout seconds (default: 40)")
    parser.add_argument("--delay-min", type=float, default=0.8, help="batch: min sleep between requests")
    parser.add_argument("--delay-max", type=float, default=1.6, help="batch: max sleep between requests")

    args = parser.parse_args()
    outdir = Path(args.outdir)

    # Decide mode
    if args.input:
        input_csv = Path(args.input)
        jsonl_path = Path(args.jsonl) if args.jsonl else None
        exit_code = run_batch(
            input_csv, outdir, jsonl_path, args.cookie_file, args.timeout, args.delay_min, args.delay_max
        )
        raise SystemExit(exit_code)
    else:
        if not args.product_id:
            parser.error("either --input (batch) or --product-id (single) must be provided")
        exit_code = run_single(
            args.product_id, args.item_id, args.vendor_item_id, outdir, args.cookie_file, args.timeout
        )
        raise SystemExit(exit_code)