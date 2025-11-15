"""Voice-controlled browser agent for visually impaired users."""

from __future__ import annotations

import asyncio
import os
import queue
import tempfile
import wave
from typing import List, Optional

import numpy as np
import pyttsx3
import sounddevice as sd
from bs4 import BeautifulSoup
from openai import OpenAI
from playwright.async_api import async_playwright

from llm_utils import VoiceBrowserLLM
from coupang_search_agent import CoupangSearchAgent, SearchResult



class KeyboardVoiceInputController:
    """Optional push-to-talk style controller using the keyboard."""

    def capture(self) -> Optional[str]:
        """Simulate opening/closing the mic with Enter and collect typed text."""
        try:
            input("\n[키보드 음성 모드] 출력이 끝났습니다. 엔터를 눌러 입력을 시작하세요.")
        except EOFError:
            return None

        try:
            text = input("[키보드 음성 모드] 명령을 입력하고 엔터를 누르세요: ").strip()
        except EOFError:
            text = ""

        try:
            input("[키보드 음성 모드] 입력을 닫으려면 다시 엔터를 눌러주세요.")
        except EOFError:
            pass
        return text or None


class SpeechInterface:
    """Handles TTS and STT for the voice browser."""

    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = None,
        stt_model: str = "gpt-4o-mini",
        samplerate: int = 16000,
        block_duration: float = 0.5,
        use_keyboard_input: bool = False,
    ):
        self.engine = pyttsx3.init()
        self.queue: queue.Queue[bytes] = queue.Queue()
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.stt_model = stt_model
        self.samplerate = samplerate
        self.block_duration = block_duration
        self.blocksize = max(1, int(samplerate * block_duration))
        self.silence_threshold = 600.0
        self.silence_duration = 1.2
        self.max_recording = 12.0
        self.use_keyboard_input = use_keyboard_input
        self.keyboard_controller = KeyboardVoiceInputController() if use_keyboard_input else None

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()

    def _audio_callback(self, indata, frames, time, status):
        self.queue.put(bytes(indata))

    def listen(self) -> Optional[str]:
        if self.use_keyboard_input and self.keyboard_controller:
            return self.keyboard_controller.capture()
        audio_bytes = self._record_audio()
        if not audio_bytes:
            return None
        return self._transcribe_audio(audio_bytes)

    def _record_audio(self) -> Optional[bytes]:
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

        chunk_duration = self.blocksize / float(self.samplerate)
        silence_chunks_required = max(1, int(self.silence_duration / chunk_duration))
        max_chunks = max(1, int(self.max_recording / chunk_duration))
        collected = bytearray()
        heard_voice = False
        silence_chunks = 0

        with sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        ):
            for _ in range(max_chunks):
                try:
                    data = self.queue.get(timeout=self.block_duration)
                except queue.Empty:
                    continue

                audio = np.frombuffer(data, dtype=np.int16)
                if not audio.size:
                    continue

                rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
                if not heard_voice:
                    if rms > self.silence_threshold:
                        heard_voice = True
                        collected.extend(data)
                    continue

                collected.extend(data)
                if rms > self.silence_threshold:
                    silence_chunks = 0
                else:
                    silence_chunks += 1
                    if silence_chunks >= silence_chunks_required:
                        break

        return bytes(collected) if collected else None

    def _transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        tmp_path = None
        uploaded_file_id = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.samplerate)
                wf.writeframes(audio_bytes)
            with open(tmp_path, "rb") as audio_file:
                uploaded = self.client.files.create(file=audio_file, purpose="input")
                uploaded_file_id = uploaded.id

            response = self.client.responses.create(
                model=self.stt_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "다음 오디오 파일을 한국어로 전사하세요. 추가 설명 없이 텍스트만 답변하세요.",
                            },
                            {
                                "type": "input_file",
                                "file_id": uploaded.id,
                            },
                        ],
                    }
                ],
            )

            text = self._extract_text_from_response(response)
            return text or None
        except Exception as exc:
            print("OpenAI 음성 인식 실패:", exc)
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if uploaded_file_id:
                try:
                    self.client.files.delete(uploaded_file_id)
                except Exception:
                    pass

    def _extract_text_from_response(self, response) -> Optional[str]:
        if getattr(response, "output", None):
            for output in response.output:
                for content in getattr(output, "content", []):
                    if getattr(content, "type", None) == "output_text":
                        text = getattr(content, "text", "").strip()
                        if text:
                            return text
        if getattr(response, "output_text", None):
            combined = " ".join(response.output_text).strip()
            if combined:
                return combined
        candidate = getattr(response, "text", "")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return None


async def extract_page_text(page, limit: int = 2000) -> str:
    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(separator="\n")
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    return body[:limit]


class VoiceBrowserAgent:
    """Main orchestration class for the voice browser."""

    def __init__(
        self,
        *,
        headless: bool = False,
        api_key: Optional[str] = "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"
,
        llm_model: str = "gpt-4o-mini",
        speech_model: str = "gpt-4o-mini",
        keyboard_input: bool = False,
    ):
        self.headless = headless
        self.speech = SpeechInterface(
            openai_api_key=api_key,
            stt_model=speech_model,
            use_keyboard_input=keyboard_input,
        )
        self.llm = VoiceBrowserLLM(api_key=api_key, model=llm_model)
        self._coupang_agent: Optional[CoupangSearchAgent] = None
        self.keyboard_input = keyboard_input

    async def run(self):
        self.speech.speak("Voice browser를 시작합니다.")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            if self.keyboard_input:
                print(
                    "\n[키보드 음성 모드] 안내: 음성 출력이 끝난 뒤 엔터를 눌러 입력을 열고, "
                    "명령을 입력한 뒤 다시 엔터를 눌러 입력을 닫아주세요."
                )

            try:
                while True:
                    self.speech.speak("명령을 말씀해주세요.")
                    user_text = self.speech.listen()
                    if not user_text:
                        self.speech.speak("명령을 인식하지 못했습니다. 다시 말씀해주세요.")
                        continue

                    self.speech.speak(f"들었습니다: {user_text}")

                    augmented = self.llm.augment_command(user_text)
                    if augmented != user_text:
                        self.speech.speak(f"명령을 보완했습니다: {augmented}")

                    cmd = self.llm.parse_command(augmented)
                    action = cmd.get("action")
                    error = cmd.get("error")

                    if error == "invalid_json":
                        self.speech.speak("명령을 이해하지 못했습니다. 다시 말씀해주세요.")
                        continue
                    if error == "llm_failure":
                        self.speech.speak("명령 해석에 문제가 있습니다. 잠시 후 다시 시도해주세요.")
                        continue

                    await self._handle_action(action, cmd, page)
            finally:
                await browser.close()

    def _ensure_coupang_agent(self, page) -> CoupangSearchAgent:
        if self._coupang_agent is None or self._coupang_agent.page is not page:
            self._coupang_agent = CoupangSearchAgent(page)
        return self._coupang_agent

    async def _handle_action(self, action: Optional[str], cmd: dict, page):
        if action == "open_url":
            url = cmd.get("url")
            if not url:
                self.speech.speak("URL 정보가 없습니다.")
                return
            self.speech.speak(f"{url} 사이트를 여는 중입니다.")
            await page.goto(url)

        elif action == "search":
            query = cmd.get("query")
            if not query:
                self.speech.speak("검색어가 없습니다.")
                return
            self.speech.speak(f"구글에서 '{query}' 검색합니다.")
            await page.goto(f"https://www.google.com/search?q={query}")

        elif action == "read_page":
            text = await extract_page_text(page)
            self.speech.speak("페이지 내용을 읽어드리겠습니다.")
            self.speech.speak(text)

        elif action == "summarize_page":
            text = await extract_page_text(page)
            self.speech.speak("페이지를 요약해서 전달해드릴게요.")
            summary = self.llm.summarize_page(text)
            self.speech.speak(summary)

        elif action == "click_link":
            target_text = cmd.get("text")
            if not target_text:
                self.speech.speak("찾을 링크 텍스트가 없습니다.")
                return
            self.speech.speak(f"{target_text} 링크를 찾습니다.")
            try:
                await page.get_by_text(target_text).first.click()
            except Exception:
                self.speech.speak("링크를 찾지 못했습니다.")

        elif action == "coupang_search":
            await self._handle_coupang_search(cmd, page)

        else:
            self.speech.speak("무슨 뜻인지 잘 모르겠어요.")

    async def _handle_coupang_search(self, cmd: dict, page):
        query = cmd.get("query")
        max_results = cmd.get("max_results", 5)
        if not query:
            self.speech.speak("쿠팡에서 검색할 키워드를 알려주세요.")
            return

        agent = self._ensure_coupang_agent(page)
        self.speech.speak(f"쿠팡에서 '{query}' 상품을 DOM으로 살펴볼게요.")
        try:
            try:
                max_count = int(max_results)
            except (TypeError, ValueError):
                max_count = 5
            max_count = max(1, min(10, max_count))
            results = await agent.search(query, max_results=max_count)
        except Exception as exc:  # noqa: BLE001
            print("쿠팡 검색 중 오류:", exc)
            self.speech.speak("쿠팡 검색 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.")
            return

        if not results:
            self.speech.speak("검색 결과가 없습니다.")
            return

        spoken_lines = self._format_results_for_voice(results)
        for line in spoken_lines:
            self.speech.speak(line)

    def _format_results_for_voice(self, results: List[SearchResult]) -> List[str]:
        """Convert DOM search results into short spoken sentences."""
        sentences: List[str] = ["쿠팡 인기 상품 상위 결과입니다."]
        for result in results:
            fragment = f"{result.rank}번 {result.title}, 가격 {result.price}"
            if result.rating:
                fragment += f", 평점 {result.rating}"
            sentences.append(fragment)
        sentences.append("필요하시면 특정 상품을 열어달라고 말씀해주세요.")
        return sentences

async def run_voice_browser(headless: bool = False, keyboard_input: bool = False):
    agent = VoiceBrowserAgent(headless=headless, keyboard_input=keyboard_input)
    await agent.run()


def main():
    keyboard_env = os.getenv("VOICE_BROWSER_KEYBOARD", "")
    keyboard_mode = keyboard_env.strip().lower() in {"1", "true", "yes", "on"}
    asyncio.run(run_voice_browser(keyboard_input=keyboard_mode))


if __name__ == "__main__":
    main()
