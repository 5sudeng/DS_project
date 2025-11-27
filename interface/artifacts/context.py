"""Context and result dataclasses for artifact collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from core.utils import ScenarioPaths


@dataclass
class ArtifactCollectionResult:
    """Result of the artifact collection process."""
    summary: Dict[str, Any]
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths
    chunk_file: Optional[str]


@dataclass
class ArtifactContext:
    """Context object holding state for a single collection run."""
    product_url: str
    product_id: str
    item_id: Optional[str]
    vendor_item_id: Optional[str]
    paths: ScenarioPaths
    btf_dir: Path
    btf_images_dir: Path
    ocr_results_file: Path
    btf_image_mapping: Dict[str, str] = None  # URL -> local path mapping for multimodal RAG

    def __post_init__(self):
        if self.btf_image_mapping is None:
            self.btf_image_mapping = {}

    def update_ids_from_url(self, url: Optional[str]) -> None:
        """Update item_id and vendor_item_id from a resolved URL."""
        if not url:
            return
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.item_id = self.item_id or (query.get("itemId") or [None])[0]
        self.vendor_item_id = self.vendor_item_id or (query.get("vendorItemId") or [None])[0]
