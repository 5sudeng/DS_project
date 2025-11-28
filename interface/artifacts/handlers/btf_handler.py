"""Handler for BTF (Below The Fold) content and image downloading."""

import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from scrapers.product_detail_scraper import ProductDetailScraper
from interface.artifacts.context import ArtifactContext


class BTFHandler:
    """Handles BTF content fetching and image downloading."""

    def __init__(self, scraper: ProductDetailScraper):
        self.scraper = scraper

    def fetch_and_process(self, ctx: ArtifactContext) -> Dict[str, Any]:
        """Fetch BTF content and download images."""
        resp, payload = self.scraper.fetch(
            ctx.product_id,
            ctx.item_id,
            ctx.vendor_item_id,
            outdir=None,
        )

        json_path: Optional[Path] = None
        if ctx.btf_dir:
            json_path = ctx.btf_dir / f"btf_{ctx.product_id}_{int(time.time() * 1000)}.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        normalized_payload = payload.get("response", payload) if isinstance(payload, dict) else payload
        image_urls = self._extract_btf_image_urls(ctx, normalized_payload)
        downloaded, url_to_path = self._download_btf_images(ctx, image_urls)

        return {
            "status": resp.status_code,
            "api_url": resp.url,
            "json_file": str(json_path) if json_path else None,
            "raw_image_urls": image_urls,
            "downloaded_images": downloaded,
            "image_count": len(downloaded),
            "image_url_to_path": url_to_path,  # For multimodal RAG
        }

    def _extract_btf_image_urls(self, ctx: ArtifactContext, payload: Any) -> List[str]:
        urls: Set[str] = set()
        if isinstance(payload, dict):
            details = payload.get("details") or []
            for detail_block in details:
                if not isinstance(detail_block, dict):
                    continue
                descriptions = detail_block.get("vendorItemContentDescriptions") or []
                for desc in descriptions:
                    if (
                        isinstance(desc, dict)
                        and desc.get("detailType") == "IMAGE"
                        and desc.get("content")
                    ):
                        urls.add(self._normalize_image_url(desc["content"]))

        try:
            serialized = json.dumps(payload, ensure_ascii=False)
            for match in re.findall(r'(//[^"\\s]+image/(?:retail|vendor|product)/[^"\\s]+)', serialized):
                urls.add(self._normalize_image_url(match))
        except TypeError:
            pass

        return [u for u in urls if u]

    def _download_btf_images(self, ctx: ArtifactContext, urls: List[str]) -> tuple[List[str], Dict[str, str]]:
        """Download images and return both paths and URL-to-path mapping."""
        if not urls:
            return [], {}

        saved: List[str] = []
        url_to_path: Dict[str, str] = {}
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        for url in urls:
            normalized = self._normalize_image_url(url)
            if not normalized:
                continue
            filename = self._btf_image_filename(ctx, normalized)
            path = ctx.btf_images_dir / filename
            if path.exists():
                saved.append(str(path))
                url_to_path[normalized] = str(path)
                continue
            try:
                urllib.request.urlretrieve(normalized, path)
                saved.append(str(path))
                url_to_path[normalized] = str(path)
            except Exception:
                continue
        return saved, url_to_path

    def _btf_image_filename(self, ctx: ArtifactContext, url: str) -> str:
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        return f"btf_{ctx.product_id}_{digest}{ext}"

    def _normalize_image_url(self, url: str) -> str:
        if not url:
            return ""
        cleaned = url.strip().rstrip("\\")
        if cleaned.startswith("//"):
            return "https:" + cleaned
        return cleaned
