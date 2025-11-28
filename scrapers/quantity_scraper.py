"""Quantity Info Scraper for Coupang products."""

import json
import logging
import random
import shlex
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import requests
from urllib.parse import urlencode
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

URL = "https://www.coupang.com/next-api/products/quantity-info"

# Initialize fake user agent generator
try:
    ua_generator = UserAgent()
    # Get a random Chrome user agent at module load
    UA = ua_generator.chrome
    logger.info("Using randomized User-Agent: %s", UA[:50] + "...")
except Exception as e:
    # Fallback to static UA if fake-useragent fails
    logger.warning("Failed to initialize FakeUserAgent, using static UA: %s", e)
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


class IPv4OnlyResolver:
    """Force IPv4 resolution."""
    def __enter__(self):
        self._orig = socket.getaddrinfo
        def _ipv4_only(*a, **k):
            res = self._orig(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res
        socket.getaddrinfo = _ipv4_only
        return self
    def __exit__(self, *exc):
        socket.getaddrinfo = self._orig


class QuantityScraper:
    """Scraper for product quantity and pricing info."""

    def __init__(self, cookie: Optional[str] = None, timeout: int = 60):
        self.cookie = cookie
        self.timeout = timeout

    def fetch(
        self,
        product_id: str,
        item_id: str,
        vendor_item_id: str,
        outdir: Optional[Path] = None,
        filename_prefix: str = "quantity_info",
    ) -> Tuple[object, dict]:
        """
        Fetch quantity info with robust fallbacks.
        Returns (response_like, data).
        """
        referer = self._build_referer(product_id, item_id, vendor_item_id)
        headers = self._build_headers(referer)
        params = self._build_params(product_id, item_id, vendor_item_id)

        logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

        save_dir = outdir if outdir else Path.cwd()
        save_dir.mkdir(parents=True, exist_ok=True)

        with IPv4OnlyResolver():
            # [변경] 1순위: curl_cffi (가장 강력한 우회)
            status, url, text, data = self._try_curl_cffi(headers, params)
            
            # 2순위: httpx
            if data is None:
                status, url, text, data = self._try_httpx(headers, params)
            
            # 3순위: requests
            if data is None:
                status, url, text, data = self._try_requests(headers, params)
            
            # 4순위: curl (시스템 명령)
            if data is None:
                status, url, text, data = self._try_curl(headers, params, save_dir)

        if data is None:
            raise RuntimeError("failed to fetch quantity-info (All methods blocked)")

        ts = int(time.time() * 1000)
        out_path = self._save_json(data, save_dir, f"{filename_prefix}_{product_id}_{ts}.json")
        logger.info("Fetched quantity info: status=%s len=%d saved=%s", status, len(text) if text else 0, out_path)

        resp = SimpleNamespace(status_code=status, url=url)
        return resp, data

    def _build_referer(self, product_id: str, item_id: str, vendor_item_id: str) -> str:
        return f"https://www.coupang.com/vp/products/{product_id}?itemId={item_id}&vendorItemId={vendor_item_id}"

    def _build_headers(self, referer: str) -> Dict[str, str]:
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
            # [변경] Chrome 131 버전에 맞는 sec-ch-ua 헤더
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua-mobile": "?0",
            "x-coupang-target-market": "KR",
            "x-coupang-accept-language": "ko-KR",
        }
        if self.cookie:
            h["cookie"] = self.cookie
        return h

    def _build_params(self, product_id: str, item_id: str, vendor_item_id: str) -> Dict[str, str]:
        return {
            "productId": product_id,
            "vendorItemId": vendor_item_id,
            "deliveryToggle": "false",
            "landingItemId": item_id,
            "landingProductId": product_id,
            "landingVendorItemId": vendor_item_id,
        }

    # [추가] curl_cffi 메서드 구현 (TLS Fingerprint 우회)
    def _try_curl_cffi(self, headers: Dict[str, str], params: Dict[str, str]) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            logger.warning("curl_cffi not installed. Skipping robust TLS fetch.")
            return None, None, None, None

        try:
            # impersonate="chrome" 옵션으로 리얼 브라우저 흉내
            r = cffi_requests.get(
                URL, 
                params=params, 
                headers=headers, 
                impersonate="chrome", 
                timeout=float(self.timeout)
            )
            
            text = r.text or ""
            if r.status_code == 200 and text:
                # 403 Access Denied 페이지가 200으로 오는 경우 체크
                if "Access Denied" in text:
                    logger.warning("[curl_cffi] blocked (Access Denied page)")
                    return None, None, None, None

                ctype = r.headers.get("content-type", "")
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    if "application/json" in ctype:
                        logger.warning("[curl_cffi] JSON decode failed but header says JSON")
                        return None, None, None, None
                    data = {"raw_text": text}
                
                logger.debug("[curl_cffi] status: %s url: %s", r.status_code, r.url)
                return r.status_code, r.url, text, data
            else:
                logger.warning(f"[curl_cffi] unexpected status {r.status_code}")
                return None, None, None, None

        except Exception as e:
            logger.warning("[curl_cffi] failed: %s", e)
            return None, None, None, None

    def _try_httpx(self, headers: Dict[str, str], params: Dict[str, str]) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
        try:
            import httpx
        except ImportError:
            return None, None, None, None
        try:
            client = httpx.Client(
                http2=True, headers=headers, params=params,
                timeout=httpx.Timeout(15.0, connect=5.0, read=float(self.timeout), write=float(self.timeout)),
                follow_redirects=True
            )
            with client as c:
                r = c.get(URL)
            text = r.text or ""
            if r.status_code == 200 and text:
                ctype = r.headers.get("content-type", "")
                data = r.json() if ctype.startswith("application/json") else {"raw_text": text}
                logger.debug("[httpx/h2] status: %s url: %s", r.status_code, r.url)
                return r.status_code, str(r.url), text, data
            else:
                # raise RuntimeError 대신 조용히 실패 처리하고 다음 단계로 넘김
                logger.warning(f"[httpx/h2] unexpected status {r.status_code}")
                return None, None, None, None
        except Exception as e:
            logger.warning("[httpx/h2] failed: %s", e)
            return None, None, None, None

    def _try_requests(self, headers: Dict[str, str], params: Dict[str, str], retries: int = 3) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                r = requests.get(URL, headers=headers, params=params, timeout=(5, 10))
                text = r.text or ""
                if r.status_code == 200 and text:
                    ctype = r.headers.get("content-type", "")
                    try:
                        data = r.json()
                    except (json.JSONDecodeError, ValueError):
                        data = {"raw_text": text}
                    logger.debug("[requests] status: %s url: %s", r.status_code, r.url)
                    return r.status_code, r.url, text, data
                else:
                    raise RuntimeError(f"requests unexpected status {r.status_code}")
            except Exception as e:
                last_err = e
                delay = (2 ** (attempt - 1)) + random.uniform(0, 0.7)
                logger.warning("[requests retry %d/%d] error: %s -> wait %.2fs", attempt, retries, e, delay)
                time.sleep(delay)
        
        return None, None, None, None

    def _try_curl(self, headers: Dict[str, str], params: Dict[str, str], outdir: Path) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[Dict]]:
        full_url = URL + "?" + urlencode(params)
        tmp_path = outdir / "_curl_quantity_tmp.json"
        
        header_flags: List[str] = []
        for k in [
            "accept","accept-language","user-agent","referer","origin","x-requested-with",
            "sec-fetch-mode","sec-fetch-site","sec-fetch-dest","sec-ch-ua","sec-ch-ua-platform",
            "sec-ch-ua-mobile","connection","x-coupang-target-market","x-coupang-accept-language"
        ]:
            if k in headers:
                header_flags += ["-H", f"{k}: {headers[k]}"]
        if self.cookie:
            header_flags += ["-H", f"cookie: {self.cookie}"]

        curl_cmd = [
            "curl","--silent","--show-error","--location",
            "--http1.1","--ipv4","--compressed",
            "--connect-timeout","5","--max-time", str(max(15, int(self.timeout))),
            *header_flags, full_url, "-o", str(tmp_path)
        ]
        logger.info("[fallback] curl: %s", " ".join(shlex.quote(c) for c in curl_cmd))
        try:
            subprocess.run(curl_cmd, check=True)
        except subprocess.CalledProcessError as ce:
            logger.warning("[fallback] curl exit: %s", ce.returncode)

        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            raw = tmp_path.read_text(encoding="utf-8", errors="ignore")
            # 403 체크
            if "Access Denied" in raw or "<TITLE>Access Denied</TITLE>" in raw:
                 logger.warning("[fallback] curl also blocked (Access Denied)")
                 return None, None, None, None
                 
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw_text": raw}
            logger.info("[fallback] curl read from file")
            return 200, full_url, raw, data
        return None, None, None, None

    def _save_json(self, obj, outdir: Path, filename: str) -> Path:
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / filename
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return p