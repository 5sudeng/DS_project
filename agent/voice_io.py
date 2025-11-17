"""Input/output helpers for the voice browser."""

from __future__ import annotations

import os
import queue
import tempfile
import wave
from typing import Optional

import numpy as np
import pyttsx3
import sounddevice as sd
from openai import OpenAI


class KeyboardVoiceInputController:
    """Optional push-to-talk style controller using the keyboard."""

    def capture(self) -> Optional[str]:
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


class TextInterface:
    """Simple text-based replacement for speech IO."""

    def speak(self, text: str):
        print(f"[Assistant] {text}")

    def listen(self) -> Optional[str]:
        try:
            user_input = input("\n[텍스트 모드] 명령을 입력하세요 (exit로 종료): ").strip()
        except EOFError:
            return None
        return user_input or None


class SpeechInterface:
    """Handles TTS and STT for the voice browser."""

    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = "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"
,
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

            return self._extract_text_from_response(response)
        except Exception as exc:  # noqa: BLE001
            print("OpenAI 음성 인식 실패:", exc)
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if uploaded_file_id:
                try:
                    self.client.files.delete(uploaded_file_id)
                except Exception:  # noqa: BLE001
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
