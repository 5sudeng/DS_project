"""Handler for content chunking."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

from processors.chunker import ContentChunker
from interface.artifacts.context import ArtifactContext

logger = logging.getLogger(__name__)


class ChunkingHandler:
    """Handles creating chunks from collected artifacts."""

    def build_dataset(self, ctx: ArtifactContext) -> Optional[Dict[str, Any]]:
        """Build chunk dataset from collected files."""
        chunker = ContentChunker()
        processed_sources: Set[str] = set()

        def _read_text(path: Path) -> Optional[str]:
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    return handle.read()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to read text file %s", path)
                return None

        def _read_json(path: Path) -> Optional[Any]:
            text = _read_text(path)
            if text is None:
                return None
            try:
                return json.loads(text)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to parse JSON file %s", path)
                return None

        html_dir = ctx.paths.html_dir
        if html_dir.exists():
            for html_file in html_dir.glob("*.html"):
                html_text = _read_text(html_file)
                if not html_text:
                    continue
                try:
                    chunker.process_html(html_file.name, html_text)
                    processed_sources.add("html")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking HTML failed for %s", html_file)

        reviews_dir = ctx.paths.reviews_dir
        if reviews_dir.exists():
            for review_file in reviews_dir.glob("*.json"):
                data = _read_json(review_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_reviews(review_file.name, data)
                    processed_sources.add("reviews")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking review file failed for %s", review_file)

        inquiries_dir = ctx.paths.inquiries_dir
        if inquiries_dir.exists():
            for inquiry_file in inquiries_dir.glob("*.json"):
                data = _read_json(inquiry_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_inquiries(inquiry_file.name, data)
                    processed_sources.add("inquiries")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking inquiry file failed for %s", inquiry_file)

        quantity_dir = ctx.paths.quantity_dir
        if quantity_dir.exists():
            for quantity_file in quantity_dir.glob("*.json"):
                data = _read_json(quantity_file)
                if not isinstance(data, list):
                    continue
                try:
                    chunker.process_quantity_json(quantity_file.name, data)
                    processed_sources.add("quantity")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking quantity file failed for %s", quantity_file)

        btf_dir = ctx.btf_dir
        if btf_dir.exists():
            for btf_file in btf_dir.glob("*.json"):
                data = _read_json(btf_file)
                if not isinstance(data, dict):
                    continue
                try:
                    chunker.process_btf_json(btf_file.name, data)
                    processed_sources.add("btf")
                except Exception:  # noqa: BLE001
                    logger.exception("Chunking BTF file failed for %s", btf_file)

        if not chunker.all_chunks:
            return None

        output_path = ctx.paths.run_dir / "chunked_data_output.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(chunker.all_chunks, handle, ensure_ascii=False, indent=2)

        return {
            "file": str(output_path),
            "chunk_count": len(chunker.all_chunks),
            "sources": sorted(processed_sources),
        }
