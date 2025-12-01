"""Service for extracting product information from web pages."""

import logging
from typing import Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ProductInfoParser:
    """Extracts product information from loaded pages."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def extract_product_name(self, fallback_url: str = "") -> str:
        """
        Extract product name from page using multiple strategies.
        
        Args:
            fallback_url: URL to use for fallback product name generation
            
        Returns:
            Product name string (never None)
        """
        logger.info("Extracting product name from page")
        
        # Strategy 1: Parse from page title
        product_name = await self._extract_from_title()
        if product_name:
            logger.info("Product name extracted from title: %s", product_name[:50])
            return product_name
        
        # Strategy 2: Look for product name in common CSS selectors
        product_name = await self._extract_from_selectors()
        if product_name:
            logger.info("Product name extracted from selector: %s", product_name[:50])
            return product_name
        
        # Strategy 3: Fallback to URL-based name
        fallback = self._generate_fallback_name(fallback_url)
        logger.warning("Using fallback product name: %s", fallback)
        return fallback
    
    async def _extract_from_title(self) -> Optional[str]:
        """Extract product name from page title."""
        try:
            title = await self.page.title()
            if title and len(title.strip()) > 0:
                # Parse title - typically "Product Name | Coupang"
                product_name = title.split("|")[0].strip() if "|" in title else title.strip()
                
                # Validate it's not just the site name
                if product_name and product_name != "쿠팡!" and len(product_name) >= 2:
                    return product_name
        except Exception as e:
            logger.warning("Failed to extract from title: %s", e)
        
        return None
    
    async def _extract_from_selectors(self) -> Optional[str]:
        """Extract product name from common CSS selectors."""
        selectors = [
            "h1.prod-buy-header__title",
            "h2.prod-buy-header__title",
            "h1.product-title",
            "h2.product-title",
            ".product-name",
            "[class*='product-title']",
            "[class*='prod-title']",
        ]
        
        for selector in selectors:
            try:
                elem = self.page.locator(selector).first
                if await elem.count() > 0:
                    product_name = await elem.inner_text()
                    product_name = product_name.strip()
                    if product_name and len(product_name) >= 2:
                        logger.debug("Found product name with selector %s", selector)
                        return product_name
            except Exception as e:
                logger.debug("Selector %s failed: %s", selector, e)
                continue
        
        return None
    
    def _generate_fallback_name(self, url: str) -> str:
        """Generate a fallback product name from URL."""
        if url:
            url_part = url.split('/')[-1][:20]
            return f"상품 ({url_part})"
        return "상품 (정보 없음)"
