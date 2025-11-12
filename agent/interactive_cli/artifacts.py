"""Artifact collection helpers for the interactive shopping CLI."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

from agent.coupang_scenario_pipeline import ScenarioPaths, parse_product_identifiers
from crawling.btf import fetch_btf
from crawling.fetch_html import fetch_html as fetch_product_html
from crawling.inquiries import fetch_inquiries
from crawling.quantity import fetch_quantity_info
from crawling.review import fetch_reviews


@dataclass
class ArtifactCollectionResult:
    summary: Dict[str, Any]
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths


@dataclass
class _ArtifactContext:
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths
    btf_dir: Path
    btf_images_dir: Path

    def update_ids_from_url(self, url: Optional[str]) -> None:
        if not url:
            return
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.item_id = self.item_id or (query.get("itemId") or [None])[0]
        self.vendor_item_id = self.vendor_item_id or (query.get("vendorItemId") or [None])[0]


class ProductArtifactCollector:
    """Collects product artifacts using the existing crawling utilities."""

    def __init__(self, *, run_dir: Optional[str], cookie: Optional[str]):
        self.run_dir = run_dir
        self.cookie = cookie

    async def collect(self, product_url: str) -> ArtifactCollectionResult:
        ctx = self._prepare_context(product_url)
        summary = await asyncio.to_thread(self._collect_sync, ctx)
        return ArtifactCollectionResult(
            summary=summary,
            product_id=ctx.product_id,
            item_id=ctx.item_id,
            vendor_item_id=ctx.vendor_item_id,
            paths=ctx.paths,
        )

    def _prepare_context(self, product_url: str) -> _ArtifactContext:
        product_id, item_id, vendor_item_id = parse_product_identifiers(product_url)
        paths = ScenarioPaths.build(self.run_dir, product_id)
        btf_dir = paths.run_dir / "btf"
        btf_images_dir = btf_dir / "images"
        btf_dir.mkdir(parents=True, exist_ok=True)
        btf_images_dir.mkdir(parents=True, exist_ok=True)
        return _ArtifactContext(
            product_id=product_id,
            item_id=item_id,
            vendor_item_id=vendor_item_id,
            paths=paths,
            btf_dir=btf_dir,
            btf_images_dir=btf_images_dir,
        )

    def _collect_sync(self, ctx: _ArtifactContext) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []

        def record(name: str, status: str, details: Dict[str, Any]) -> None:
            serialized = {k: (str(v) if isinstance(v, Path) else v) for k, v in details.items()}
            steps.append({"name": name, "status": status, "details": serialized})

        # HTML
        try:
            resp, soup, out_path = fetch_product_html(
                ctx.product_id,
                ctx.item_id or "",
                ctx.vendor_item_id or "",
                cookie=self.cookie,
                timeout=40,
                outdir=ctx.paths.html_dir,
            )
            ctx.update_ids_from_url(resp.url)
            record(
                "fetch_html",
                "success",
                {
                    "status": resp.status_code,
                    "url": resp.url,
                    "file": out_path,
                    "title": soup.title.text.strip() if soup.title else "",
                    "resolved_item_id": ctx.item_id,
                    "resolved_vendor_item_id": ctx.vendor_item_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_html", "error", {"error": str(exc)})

        # Reviews
        try:
            review_pages = 1
            review_page_size = 20
            page_records: List[Dict[str, Any]] = []
            for page_no in range(1, review_pages + 1):
                resp, data = fetch_reviews(
                    product_id=ctx.product_id,
                    vendor_item_id=ctx.vendor_item_id,
                    item_id=ctx.item_id,
                    cookie=self.cookie,
                    page=page_no,
                    size=review_page_size,
                    outdir=str(ctx.paths.reviews_dir),
                    retries=2,
                )
                page_records.append(
                    {
                        "page": page_no,
                        "status": resp.status_code,
                        "response_keys": list(data.keys()),
                    }
                )
            record(
                "fetch_reviews",
                "success",
                {"output_dir": ctx.paths.reviews_dir, "pages": page_records},
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_reviews", "error", {"error": str(exc)})

        # Inquiries
        try:
            resp, data = fetch_inquiries(
                product_id=ctx.product_id,
                page_no=1,
                cookie=self.cookie,
                item_id=ctx.item_id,
                vendor_item_id=ctx.vendor_item_id,
                outdir=str(ctx.paths.inquiries_dir),
                retries=2,
                is_preview=True,
            )
            record(
                "fetch_inquiries",
                "success",
                {
                    "output_dir": ctx.paths.inquiries_dir,
                    "status": resp.status_code,
                    "response_keys": list(data.keys()),
                    "page_no": 1,
                },
            )
        except Exception as exc:  # noqa: BLE001
            record("fetch_inquiries", "error", {"error": str(exc)})

        # Quantity
        if ctx.item_id and ctx.vendor_item_id:
            try:
                resp, data = fetch_quantity_info(
                    ctx.product_id,
                    ctx.item_id,
                    ctx.vendor_item_id,
                    cookie=self.cookie,
                    outdir=str(ctx.paths.quantity_dir),
                )
                record(
                    "fetch_quantity",
                    "success",
                    {
                        "status": resp.status_code,
                        "output_dir": ctx.paths.quantity_dir,
                        "keys": list(data.keys()),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                record("fetch_quantity", "error", {"error": str(exc)})
        else:
            record(
                "fetch_quantity",
                "skipped",
                {"reason": "itemId 또는 vendorItemId가 없어 quantity 수집을 건너뜁니다."},
            )

        # BTF payload + images
        try:
            btf_details = self._fetch_btf_assets(ctx)
            record("fetch_btf", "success", btf_details)
        except Exception as exc:  # noqa: BLE001
            record("fetch_btf", "error", {"error": str(exc)})

        return {
            "product_id": ctx.product_id,
            "item_id": ctx.item_id,
            "vendor_item_id": ctx.vendor_item_id,
            "paths": {
                "run_dir": str(ctx.paths.run_dir),
                "html_dir": str(ctx.paths.html_dir),
                "reviews_dir": str(ctx.paths.reviews_dir),
                "inquiries_dir": str(ctx.paths.inquiries_dir),
                "quantity_dir": str(ctx.paths.quantity_dir),
                "btf_dir": str(ctx.btf_dir),
                "btf_images_dir": str(ctx.btf_images_dir),
            },
            "steps": steps,
        }

    def _fetch_btf_assets(self, ctx: _ArtifactContext) -> Dict[str, Any]:
        resp, payload = fetch_btf(
            ctx.product_id,
            ctx.item_id,
            ctx.vendor_item_id,
            cookie=self.cookie,
            outdir=None,
            retries=2,
        )

        json_path: Optional[Path] = None
        if ctx.btf_dir:
            json_path = ctx.btf_dir / f"btf_{ctx.product_id}_{int(time.time() * 1000)}.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        normalized_payload = payload.get("response", payload) if isinstance(payload, dict) else payload
        image_urls = self._extract_btf_image_urls(ctx, normalized_payload)
        downloaded = self._download_btf_images(ctx, image_urls)

        return {
            "status": resp.status_code,
            "api_url": resp.url,
            "json_file": str(json_path) if json_path else None,
            "raw_image_urls": image_urls,
            "downloaded_images": downloaded,
            "image_count": len(downloaded),
        }

    def _extract_btf_image_urls(self, ctx: _ArtifactContext, payload: Any) -> List[str]:
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

    def _download_btf_images(self, ctx: _ArtifactContext, urls: List[str]) -> List[str]:
        if not urls:
            return []

        saved: List[str] = []
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
                continue
            try:
                urllib.request.urlretrieve(normalized, path)
                saved.append(str(path))
            except Exception:
                continue
        return saved

    def _btf_image_filename(self, ctx: _ArtifactContext, url: str) -> str:
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
