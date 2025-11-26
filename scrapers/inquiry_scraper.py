"""Inquiry Scraper for Coupang products."""

import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

URL = "https://www.coupang.com/next-api/products/inquiries"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


class InquiryScraper:
    """Scraper for product inquiries."""

    def __init__(self, cookie: Optional[str] = None, retries: int = 2):
        self.cookie = cookie
        self.retries = retries

    def fetch(
        self,
        product_id: str,
        page_no: int = 1,
        item_id: Optional[str] = None,
        vendor_item_id: Optional[str] = None,
        outdir: Optional[Path] = None,
        is_preview: bool = True,
    ) -> Tuple[requests.Response, dict]:
        """Fetch inquiries for a product."""
        referer = self._build_referer(product_id, item_id, vendor_item_id)
        headers = self._build_headers(referer)
        params = self._build_params(product_id, page_no, is_preview)

        logger.debug("[REQUEST] %s referer=%s params=%s", URL, referer, params)

        resp = self._safe_request(URL, headers, params)
        logger.debug("status: %s url: %s", resp.status_code, resp.url)

        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}

        if outdir:
            ts = int(time.time() * 1000)
            self._save_json(data, outdir, f"inquiries_{product_id}_p{page_no}_{ts}.json")

        return resp, data

    def _build_referer(self, product_id: str, item_id: Optional[str], vendor_item_id: Optional[str]) -> str:
        base = f"https://www.coupang.com/vp/products/{product_id}"
        return f"{base}?itemId={item_id}&vendorItemId={vendor_item_id}" if (item_id and vendor_item_id) else base

    def _build_headers(self, referer: str) -> Dict[str, str]:
        h = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": UA,
            "origin": "https://www.coupang.com",
            "referer": referer,
            "x-requested-with": "XMLHttpRequest",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-fetch-dest": "empty",
        }
        if self.cookie:
            h["cookie"] = self.cookie
        return h

    def _build_params(self, product_id: str, page_no: int, is_preview: bool) -> Dict[str, str]:
        return {"productId": product_id, "pageNo": str(page_no), "isPreview": "true" if is_preview else "false"}

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
                return sess.get(url, headers=headers, params=params, timeout=(5, 10))
            except requests.Timeout as e:
                last_err = e
                delay = (2 ** attempt) * 0.8 + random.uniform(0, 0.6)
                logger.warning("[retry %d/%d] timeout → wait %.2fs", attempt + 1, self.retries, delay)
                time.sleep(delay)
            except requests.RequestException as e:
                last_err = e
                logger.warning("[retry %d/%d] error: %s", attempt + 1, self.retries, e)
                time.sleep(1.0)
        raise last_err or RuntimeError("request failed")

    def _save_json(self, obj, outdir: Path, filename: str) -> Path:
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / filename
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("saved → %s", p)
        return p
