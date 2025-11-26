"""HTML Fetcher for Coupang products."""

import logging
import random
import shlex
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


class IPv4OnlyResolver:
    """Force IPv4 resolution to avoid IPv6 issues."""
    def __enter__(self):
        self._orig = socket.getaddrinfo
        def _ipv4_only(*a, **k):
            res = self._orig(*a, **k)
            return [r for r in res if r[0] == socket.AF_INET] or res
        socket.getaddrinfo = _ipv4_only
        return self
    def __exit__(self, *exc):
        socket.getaddrinfo = self._orig


class HtmlFetcher:
    """Fetcher for Coupang product HTML pages."""

    def __init__(self, timeout: int = 60, cookie: Optional[str] = None):
        self.timeout = timeout
        self.cookie = cookie

    def fetch(
        self,
        product_id: str,
        item_id: str,
        vendor_item_id: str,
        outdir: Optional[Path] = None,
    ) -> Tuple[object, BeautifulSoup, Path]:
        """
        Fetch Coupang product HTML.
        Returns (response_like, BeautifulSoup, saved_path).
        """
        base_url, candidates = self._candidate_urls(product_id, item_id, vendor_item_id)
        headers = self._build_headers(base_url, item_id, vendor_item_id)

        with IPv4OnlyResolver():
            status, url, text = self._try_httpx(candidates, headers)
            if text is None:
                status, url, text = self._try_requests(candidates, headers)
            if text is None:
                status, url, text = self._try_curl(candidates, headers, product_id)

        if text is None:
            raise RuntimeError("failed to fetch html")

        # Save & parse
        save_dir = outdir if outdir else Path.cwd()
        save_dir.mkdir(parents=True, exist_ok=True)
        out_path = save_dir / f"response_{product_id}.html"
        out_path.write_text(text, encoding="utf-8")

        logger.info("Fetched HTML: status=%s len=%d saved=%s", status, len(text), out_path)

        soup = BeautifulSoup(text, "html.parser")
        title = soup.title.text.strip() if soup.title else "(no title)"
        logger.debug("Page title: %s", title)

        resp_like = SimpleNamespace(status_code=status, url=url, text=text)
        return resp_like, soup, out_path

    def _candidate_urls(self, product_id: str, item_id: str, vendor_item_id: str) -> Tuple[str, List[Tuple[str, Optional[dict]]]]:
        base_url = f"https://www.coupang.com/vp/products/{product_id}"
        params_full = {"itemId": item_id, "vendorItemId": vendor_item_id}
        cands = [
            (base_url, None),              # no params
            (base_url, params_full),       # with ids
            (base_url, {"pageSize": "1"}), # tiny page variant
        ]
        return base_url, cands

    def _build_headers(self, base_url: str, item_id: str, vendor_item_id: str) -> dict:
        h = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "user-agent": UA,
            "referer": f"{base_url}?itemId={item_id}&vendorItemId={vendor_item_id}",
            "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="99", "Google Chrome";v="141"',
            "sec-ch-ua-platform": '"macOS"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "cache-control": "max-age=0",
        }
        if self.cookie:
            h["cookie"] = self.cookie
        return h

    def _try_httpx(self, candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        try:
            import httpx
        except ImportError:
            return None, None, None

        try:
            import h2  # noqa: F401
            use_http2 = True
        except ImportError:
            use_http2 = False

        for u, p in candidates:
            self._print_get(u, p)
            for attempt in range(1, 4):
                try:
                    timeout_cfg = httpx.Timeout(timeout=float(self.timeout), connect=10.0, read=float(self.timeout), write=float(self.timeout), pool=5.0)
                    with httpx.Client(http2=use_http2, headers=headers, timeout=timeout_cfg, follow_redirects=True) as client:
                        r = client.get(u, params=p)
                        if r.status_code == 200 and r.text:
                            logger.debug("[httpx/%s] status: %s url: %s", 'h2' if use_http2 else 'h1', r.status_code, r.url)
                            return r.status_code, str(r.url), r.text
                        else:
                            raise RuntimeError(f"httpx status {r.status_code}")
                except Exception as e:
                    delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                    logger.warning("[httpx] failed (attempt %d/3): %s, wait %.2fs", attempt, e, delay)
                    if attempt < 3:
                        time.sleep(delay)
        return None, None, None

    def _try_requests(self, candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        sess = self._make_requests_session(retries=3)
        for u, p in candidates:
            self._print_get(u, p)
            for attempt in range(1, 4):
                try:
                    r = sess.get(u, headers=headers, params=p, timeout=(10, self.timeout), allow_redirects=True)
                    if r.status_code == 200 and r.text:
                        logger.debug("[requests] status: %s url: %s", r.status_code, r.url)
                        return r.status_code, r.url, r.text
                    else:
                        raise RuntimeError(f"HTTP {r.status_code}")
                except requests.Timeout:
                    delay = (2 ** attempt) + random.uniform(1, 2)
                    logger.warning("[retry %d/3] timeout, wait %.2fs", attempt, delay)
                    time.sleep(delay)
                except requests.RequestException as e:
                    delay = (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                    logger.warning("[retry %d/3] request error: %s, wait %.2fs", attempt, e, delay)
                    time.sleep(delay)
        return None, None, None

    def _try_curl(self, candidates: Sequence[Tuple[str, Optional[dict]]], headers: dict, product_id: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        tmp_path = Path(f"_curl_html_{product_id}.html").absolute()
        header_flags = []
        for k in ["accept", "accept-language", "accept-encoding", "user-agent", "origin", "referer", "sec-ch-ua", "sec-ch-ua-platform", "sec-ch-ua-mobile", "connection"]:
            if k in headers:
                header_flags += ["-H", f"{k}: {headers[k]}"]
        if self.cookie:
            header_flags += ["-H", f"cookie: {self.cookie}"]

        for u, p in candidates:
            qs = ("?" + urlencode(p)) if p else ""
            full_url = u + qs
            curl_cmd = [
                "curl", "--silent", "--show-error", "--location",
                "--http1.1", "--ipv4", "--compressed",
                "--connect-timeout", "5",
                "--max-time", str(max(15, int(self.timeout))),
                *header_flags, full_url, "-o", str(tmp_path)
            ]
            logger.info("[fallback] curl: %s", " ".join(shlex.quote(c) for c in curl_cmd))
            try:
                subprocess.run(curl_cmd, check=True)
            except subprocess.CalledProcessError as ce:
                logger.warning("[fallback] curl exit: %s", ce.returncode)

            if tmp_path.exists() and tmp_path.stat().st_size > 0:
                return 200, full_url, tmp_path.read_text(encoding="utf-8", errors="ignore")
        return None, None, None

    def _make_requests_session(self, retries: int = 2) -> requests.Session:
        s = requests.Session()
        retry = Retry(
            total=retries, connect=retries, read=retries, status=retries,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    def _print_get(self, u: str, p: Optional[dict]):
        logger.debug("GET %s params=%s", u, p)
