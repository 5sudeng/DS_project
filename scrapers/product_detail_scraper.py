"""Product Detail (BTF) Scraper for Coupang products."""

import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
import requests
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.cookies import build_cookie_header
from core.utils import get_unique_filename

logger = logging.getLogger(__name__)

URL = "https://www.coupang.com/vp/products/sdp/contents"

# Initialize fake user agent generator
try:
    ua_generator = UserAgent()
    UA = ua_generator.chrome
    logger.info("[Product Detail Scraper] Using randomized User-Agent: %s", UA[:50] + "...")
except Exception as e:
    logger.warning("[Product Detail Scraper] Failed to initialize FakeUserAgent, using static UA: %s", e)
    UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


class ProductDetailScraper:
    """Scraper for product detail (BTF) info."""

    def __init__(self, cookie: Optional[str] = None, retries: int = 2):
        self.cookie = cookie
        self.retries = retries

    def fetch(
        self,
        product_id: str,
        item_id: Optional[str] = None,
        vendor_item_id: Optional[str] = None,
        outdir: Optional[Path] = None,
    ) -> Tuple[requests.Response, dict]:
        """Fetch BTF data for a product."""
        referer = self._build_referer(product_id, item_id, vendor_item_id)
        headers = self._build_headers(referer)
        params = self._build_params(product_id, item_id, vendor_item_id)

        logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

        resp = self._safe_request(URL, headers, params)
        logger.debug("status: %s url: %s", resp.status_code, resp.url)

        try:
            data = resp.json()
        except Exception:
            data = {"error": "JSON Decode Failed", "status_code": resp.status_code, "raw_text_start": resp.text[:200]}
            logger.warning("Warning: Response body is not JSON.")

        if outdir:
            ts = int(time.time() * 1000)
            suffix = []
            if item_id: suffix.append(f"i{item_id}")
            if vendor_item_id: suffix.append(f"v{vendor_item_id}")
            base = f"btf_{product_id}" + (("_" + "_".join(suffix)) if suffix else "")
            self._save_json(data, outdir, f"{base}_{ts}.json")

        return resp, data

    def _build_referer(self, product_id: str, item_id: Optional[str], vendor_item_id: Optional[str]) -> str:
        base = f"https://www.coupang.com/vp/products/{product_id}"
        return f"{base}?itemId={item_id}&vendorItemId={vendor_item_id}" if (item_id and vendor_item_id) else base

    def _build_headers(self, referer: str) -> Dict[str, str]:
        h = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6,zh-CN;q=0.5,zh;q=0.4,ja;q=0.3,es;q=0.2",
            "accept-encoding": "gzip, deflate, br, zstd",
            "user-agent": UA,
            "origin": "https://www.coupang.com",
            "referer": referer,
            "priority": "u=1, i",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "macOS",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if self.cookie:
            h["cookie"] = self.cookie
        return h

    def _build_params(self, product_id: str, item_id: Optional[str], vendor_item_id: Optional[str]) -> Dict[str, str]:
        params = {"productId": str(product_id)}
        if vendor_item_id:
            params["vendorItemId"] = str(vendor_item_id)
        if item_id:
            params["itemId"] = str(item_id)
        return params

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        retry = Retry(
            total=self.retries, connect=self.retries, read=self.retries, status=self.retries,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    def _safe_request(self, url: str, headers: Dict[str, str], params: Dict[str, str]) -> requests.Response:
        sess = self._make_session()
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                resp = sess.get(url, headers=headers, params=params, timeout=(5, 10))
                if resp.status_code >= 400 and resp.status_code not in [429, 500, 502, 503, 504]:
                    resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                last_err = e
                if isinstance(e, requests.Timeout):
                    delay = (2 ** attempt) * 0.8 + random.uniform(0, 0.6)
                    logger.warning("[retry %d/%d] timeout → wait %.2fs", attempt + 1, self.retries, delay)
                    time.sleep(delay)
                elif attempt < self.retries:
                    logger.warning("[retry %d/%d] error: %s", attempt + 1, self.retries, e)
                    time.sleep(1.0)
                else:
                    pass
        if last_err:
            raise last_err
        raise RuntimeError("request failed after all retries")

    def _save_json(self, obj, outdir: Path, filename: str) -> Path:
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / filename
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("saved → %s", p)
        return p
