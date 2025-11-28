"""Action handling helpers for the voice browser."""

from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from .coupang_search_agent import CoupangSearchAgent, SearchResult


async def extract_page_text(page, limit: int = 2000) -> str:
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(separator="\n")
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    return body[:limit]


def is_coupang_site(url: Optional[str]) -> bool:
    return bool(url and "coupang.com" in url)


class CoupangActionHelper:
    """Handles Coupang-specific DOM interactions."""

    def __init__(self, io):
        self.io = io
        self._agent: Optional[CoupangSearchAgent] = None

    def ensure_agent(self, page) -> CoupangSearchAgent:
        if self._agent is None or self._agent.page is not page:
            self._agent = CoupangSearchAgent(page)
        return self._agent

    async def perform_search(self, page, query: str, max_results: int = 5):
        agent = self.ensure_agent(page)
        self.io.speak(f"쿠팡에서 '{query}' 상품을 DOM으로 살펴볼게요.")
        try:
            max_count = max(1, min(10, int(max_results)))
        except (TypeError, ValueError):
            max_count = 5
        try:
            return await agent.search(query, max_results=max_count)
        except Exception as exc:  # noqa: BLE001
            print("쿠팡 검색 중 오류:", exc)
            self.io.speak("쿠팡 검색 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
            return None

    def speak_results(self, results: List[SearchResult]):
        if not results:
            self.io.speak("검색 결과가 없습니다.")
            return
        sentences = ["쿠팡 인기 상품 상위 결과입니다."]
        for result in results:
            fragment = f"{result.rank}번 {result.title}, 가격 {result.price}"
            if result.rating:
                fragment += f", 평점 {result.rating}"
            sentences.append(fragment)
        sentences.append("필요하시면 특정 상품을 열어달라고 말씀해주세요.")
        for line in sentences:
            self.io.speak(line)


class BrowserActionHandler:
    """Routes parsed actions to concrete Playwright operations."""

    def __init__(self, io, llm):
        self.io = io
        self.llm = llm
        self.coupang_helper = CoupangActionHelper(io)

    async def handle(self, action: Optional[str], cmd: dict, page, *, current_site: Optional[str] = None):
        if action == "open_url":
            await self._open_url(cmd, page)
        elif action == "search":
            await self._handle_search(cmd, page, current_site=current_site)
        elif action == "read_page":
            await self._read_page(page)
        elif action == "summarize_page":
            await self._summarize_page(page)
        elif action == "click_link":
            await self._click_link(cmd, page)
        elif action == "coupang_search":
            await self._coupang_search(cmd, page)
        else:
            self.io.speak("무슨 뜻인지 잘 모르겠어요.")

    async def _open_url(self, cmd: dict, page):
        url = cmd.get("url")
        if not url:
            self.io.speak("URL 정보가 없습니다.")
            return
        self.io.speak(f"{url} 사이트를 여는 중입니다.")
        await page.goto(url)

    async def _handle_search(self, cmd: dict, page, *, current_site: Optional[str]):
        query = cmd.get("query")
        if not query:
            self.io.speak("검색어가 없습니다.")
            return
        if is_coupang_site(current_site) or is_coupang_site(getattr(page, "url", "")):
            await self._coupang_search(cmd, page, override_query=query)
        else:
            self.io.speak(f"구글에서 '{query}' 검색합니다.")
            await page.goto(f"https://www.google.com/search?q={query}")

    async def _read_page(self, page):
        text = await extract_page_text(page)
        self.io.speak("페이지 내용을 읽어드리겠습니다.")
        self.io.speak(text)

    async def _summarize_page(self, page):
        text = await extract_page_text(page)
        self.io.speak("페이지를 요약해서 전달해드릴게요.")
        summary = self.llm.summarize_page(text)
        self.io.speak(summary)

    async def _click_link(self, cmd: dict, page):
        target_text = cmd.get("text")
        if not target_text:
            self.io.speak("찾을 링크 텍스트가 없습니다.")
            return
        self.io.speak(f"{target_text} 링크를 찾습니다.")
        try:
            await page.get_by_text(target_text).first.click()
        except Exception:  # noqa: BLE001
            self.io.speak("링크를 찾지 못했습니다.")

    async def _coupang_search(self, cmd: dict, page, *, override_query: Optional[str] = None):
        query = override_query or cmd.get("query")
        max_results = cmd.get("max_results", 5)
        if not query:
            self.io.speak("쿠팡에서 검색할 키워드를 알려주세요.")
            return
        results = await self.coupang_helper.perform_search(page, query, max_results=max_results)
        if results is None:
            return
        self.coupang_helper.speak_results(results)
