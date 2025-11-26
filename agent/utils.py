"""Shared utilities for the shopping agent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse


PRODUCT_ID_PATTERN = re.compile(r"/products/(?P<pid>\d+)")


@dataclass
class ScenarioPaths:
    """Paths for storing scenario artifacts."""
    run_dir: Path
    html_dir: Path
    reviews_dir: Path
    inquiries_dir: Path
    quantity_dir: Path
    summary_file: Path

    @classmethod
    def build(cls, base_dir: Optional[str], product_id: str) -> "ScenarioPaths":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(base_dir or "outputs/scenario_runs").expanduser()
        run_dir = base / f"{product_id}_{timestamp}"
        html_dir = run_dir / "html"
        reviews_dir = run_dir / "reviews"
        inquiries_dir = run_dir / "inquiries"
        quantity_dir = run_dir / "quantity"
        for directory in (run_dir, html_dir, reviews_dir, inquiries_dir, quantity_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return cls(
            run_dir=run_dir,
            html_dir=html_dir,
            reviews_dir=reviews_dir,
            inquiries_dir=inquiries_dir,
            quantity_dir=quantity_dir,
            summary_file=run_dir / "scenario_summary.json",
        )


def parse_product_identifiers(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Parse product identifiers from a Coupang URL."""
    match = PRODUCT_ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"URL에서 productId를 찾지 못했습니다: {url}")
    product_id = match.group("pid")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    item_id = (query.get("itemId") or [None])[0]
    vendor_item_id = (query.get("vendorItemId") or [None])[0]
    return product_id, item_id, vendor_item_id
