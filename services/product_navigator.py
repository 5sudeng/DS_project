"""Service for navigating to product pages with retries and connection management."""

import asyncio
import logging
from typing import Optional
from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


class NavigationResult:
    """Result of a navigation operation."""
    def __init__(
        self,
        success: bool,
        url: Optional[str] = None,
        error: Optional[str] = None,
        warnings: Optional[list] = None
    ):
        self.success = success
        self.url = url
        self.error = error
        self.warnings = warnings or []


class ProductNavigator:
    """Handles product page navigation with retries and error recovery."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def navigate_to_product(self, url: str) -> NavigationResult:
        """
        Navigate to a product page with retries and connection establishment.
        
        Args:
            url: Product page URL to navigate to
            
        Returns:
            NavigationResult with success status, final URL, and any warnings
        """
        logger.info("Attempting to navigate to product page: %s", url)
        warnings = []
        
        # First, try to navigate to Coupang homepage to establish connection
        try:
            logger.debug("Establishing connection to Coupang homepage")
            await self.page.goto("https://www.coupang.com", timeout=10000)
            await asyncio.sleep(0.5)
            logger.debug("Connection to Coupang established")
        except Exception as e:
            warning_msg = f"쿠팡 메인 페이지 연결 실패: {e}"
            logger.warning(warning_msg)
            warnings.append(warning_msg)
        
        # Try to load the product page with retries
        max_retries = 3
        loaded = False
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"Navigation attempt {attempt}/{max_retries}")
                response: Optional[Response] = await self.page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                
                if response and response.status == 200:
                    logger.info(f"Page loaded successfully (HTTP {response.status})")
                    loaded = True
                    break
                elif response and response.status >= 400:
                    error_msg = f"HTTP {response.status} 오류 발생"
                    logger.warning(error_msg)
                    warnings.append(error_msg)
                    if attempt < max_retries:
                        logger.debug(f"Retrying... ({attempt}/{max_retries})")
                        await asyncio.sleep(2)
                    else:
                        last_error = f"페이지 로드 실패: HTTP {response.status}"
                elif response is None:
                    last_error = "응답 없음 - 네트워크 연결 확인 필요"
                    logger.warning(last_error)
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    warning_msg = f"시도 {attempt} 실패: {str(e)[:100]}"
                    logger.warning(warning_msg)
                    warnings.append(warning_msg)
                    await asyncio.sleep(2)
                else:
                    logger.error(f"All navigation attempts failed: {e}")
        
        if not loaded:
            return NavigationResult(
                success=False,
                error=last_error or "페이지 로드 실패",
                warnings=warnings
            )
        
        # Wait for JavaScript to render
        logger.debug("Waiting for page to render")
        await asyncio.sleep(2)
        
        # Wait for key elements to be visible
        try:
            await self.page.wait_for_selector("body", timeout=5000)
        except Exception:
            pass  # Continue even if selector not found
        
        # Validate navigation result
        current_url = self.page.url
        page_content = await self.page.content()
        
        if current_url.startswith("chrome-error://") or "this site can't be reached" in page_content.lower():
            logger.warning("Chrome error page detected: %s", current_url)
            return NavigationResult(
                success=False,
                url=current_url,
                error="Chrome 오류 페이지로 리다이렉트됨",
                warnings=warnings
            )
        
        if "coupang.com" not in current_url:
            logger.warning("Unexpected domain after navigation: %s", current_url)
            return NavigationResult(
                success=False,
                url=current_url,
                error=f"예상치 못한 도메인으로 리다이렉트됨: {current_url}",
                warnings=warnings
            )
        
        logger.info("Successfully navigated to: %s", current_url)
        return NavigationResult(
            success=True,
            url=current_url,
            warnings=warnings
        )
