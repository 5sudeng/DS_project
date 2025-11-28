"""Handler for OCR processing."""

from typing import Any, Dict, Optional, Tuple

from processors.ocr_processor import OCRProcessor
from interface.artifacts.context import ArtifactContext


class OCRHandler:
    """Handles OCR processing for product images."""

    def __init__(self, processor: Optional[OCRProcessor], delay: float = 0.5, only_btf: bool = True):
        self.processor = processor
        self.delay = delay
        self.only_btf = only_btf

    def process(self, ctx: ArtifactContext) -> Tuple[str, Dict[str, Any]]:
        """Run OCR on collected images."""
        if not self.processor:
             return "skipped", {"reason": "OCR Processor not initialized"}

        # Use run_dir as the data_dir, assuming OCRProcessor handles the path structure
        results = self.processor.process_product_images(
             ctx.product_id,
             str(ctx.paths.run_dir),
             only_btf=self.only_btf
        )
        
        # Save results
        self.processor.save_results(ctx.product_id, str(ctx.paths.run_dir), results)

        success_count = sum(1 for r in results if r['success'])
        failure_count = len(results) - success_count

        return (
            "success",
            {
                "output_file": str(ctx.ocr_results_file),
                "processed_images": len(results),
                "success_count": success_count,
                "failure_count": failure_count,
                "delay_seconds": self.delay,
            },
        )
