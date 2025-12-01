"""Input/output helpers for the voice browser."""

from __future__ import annotations

import base64
import os
import queue
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import sounddevice as sd
from openai import OpenAI
import grpc  # type: ignore
import requests  # type: ignore
import pyaudio  # type: ignore
try:
    import core.vito_stt_client_pb2 as rtzr_pb  # type: ignore
    import core.vito_stt_client_pb2_grpc as rtzr_pb_grpc  # type: ignore
except ImportError:
    rtzr_pb = None
    rtzr_pb_grpc = None

# Global TTS process tracker for sequential playback
_current_tts_process = None


OPENAI_ENV_FILE =  "openai_voice_env.txt"
RTZR_ENV_FILE = "rtzr_voice_env.txt"


def _load_env_file(path: Path) -> Dict[str, str]:
    """Simple key=value parser that ignores comments and blank lines."""
    if not path.exists():
        return {}
    entries: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        entries[key.strip()] = value.strip()
    return entries


def load_openai_voice_config() -> Dict[str, Optional[str]]:
    file_env = _load_env_file(Path(OPENAI_ENV_FILE))
    return {
        "api_key": os.getenv("OPENAI_API_KEY") or file_env.get("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL") or file_env.get("OPENAI_BASE_URL"),
        "stt_model": os.getenv("STT_MODEL") or file_env.get("STT_MODEL"),
    }


def load_rtzr_voice_config() -> Dict[str, Optional[str]]:
    file_env = _load_env_file(Path(RTZR_ENV_FILE))
    return {
        "client_id": os.getenv("RTZR_CLIENT_ID") or file_env.get("RTZR_CLIENT_ID"),
        "client_secret": os.getenv("RTZR_CLIENT_SECRET") or file_env.get("RTZR_CLIENT_SECRET"),
    }



class KeyboardVoiceInputController:
    """Push-to-talk controller using keyboard (Enter to start/stop)."""

    def __init__(self, samplerate: int = 16000, channels: int = 1):
        self.samplerate = samplerate
        self.channels = channels

    def record(self) -> Optional[bytes]:
        """Record audio between two Enter key presses."""
        global _current_tts_process
        try:
            msg = "엔터를 누르면 녹음을 시작합니다"
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', msg])
            input("\n⌨️  [PTT] 엔터를 누르면 녹음을 시작합니다...")
        except EOFError:
            return None

        q = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            q.put(bytes(indata))

        # Start recording
        stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=1024,
            device=None,
            dtype="int16",
            channels=self.channels,
            callback=callback,
        )
        
        collected = bytearray()
        with stream:
            msg = "녹음 중입니다. 종료하려면 엔터를 누르세요"
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', msg])
            print("🔴 녹음 중... (종료하려면 엔터를 누르세요)")
            try:
                input()
            except EOFError:
                pass
        
        # Drain queue
        while not q.empty():
            collected.extend(q.get())

        return bytes(collected) if collected else None


class TextInterface:
    """Simple text-based replacement for speech IO."""

    def speak(self, text: str):
        global _current_tts_process
        print(f"[Assistant] {text}")
        try:
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', text])
        except Exception:
            pass

    def listen(self) -> Optional[str]:
        try:
            user_input = input("\n[텍스트 모드] 명령을 입력하세요 (exit로 종료): ").strip()
        except EOFError:
            return None
        return user_input or None


class OpenAIVoiceInterface:
    """Handles TTS and STT for the voice browser (OpenAI Whisper API)."""

    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = None,
        stt_model: Optional[str] = None,
        samplerate: int = 16000,
        block_duration: float = 0.5,
        use_keyboard_input: bool = False,
        base_url: Optional[str] = None,
    ):
        # Removed pyttsx3 - using system say command
        self.queue: queue.Queue[bytes] = queue.Queue()
        config = load_openai_voice_config()
        resolved_base = base_url or config["base_url"] or "https://api.openai.com/v1"
        resolved_key = openai_api_key or config["api_key"]
        if not resolved_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. openai_voice_env.txt 또는 환경 변수를 확인하세요.")
        self.client = OpenAI(
            api_key=resolved_key,
            base_url=resolved_base,
        )
        self.stt_model = stt_model or config["stt_model"] or "whisper-1"
        self.samplerate = samplerate
        self.block_duration = block_duration
        self.blocksize = max(1, int(samplerate * block_duration))
        self.silence_threshold = 600.0
        self.silence_duration = 1.2
        self.max_recording = 12.0
        self.use_keyboard_input = use_keyboard_input
        self.keyboard_controller = KeyboardVoiceInputController(samplerate) if use_keyboard_input else None

    def speak(self, text: str):
        global _current_tts_process
        try:
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', text])
        except Exception:
            pass

    def _audio_callback(self, indata, frames, time, status):
        self.queue.put(bytes(indata))

    def listen(self) -> Optional[str]:
        if self.use_keyboard_input and self.keyboard_controller:
            audio_bytes = self.keyboard_controller.record()
        else:
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
                        print("🎙️ 음성 감지됨 (녹음 중)")
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
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.samplerate)
                wf.writeframes(audio_bytes)

            try:
                with open(tmp_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model=self.stt_model or "whisper-1",
                        file=audio_file,
                        language="ko",
                        response_format="text",
                        temperature=0,
                    )
                text = getattr(transcript, "text", "") or ""
                if text.strip():
                    return text.strip()
            except Exception as primary_exc:  # noqa: BLE001
                print("OpenAI 음성 인식 실패:", primary_exc)
                print("ℹ️  OPENAI_BASE_URL/KEY와 stt_model(예: whisper-1)을 확인하거나 '--voice-backend vosk'로 전환하세요.")

            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


class VoskSpeechInterface:
    """Local STT using vosk-small-ko (offline)."""

    def __init__(
        self,
        *,
        model_path: str = "vosk-model-small-ko-0.22/",
        samplerate: int = 16000,
        block_duration: float = 0.5,
        use_keyboard_input: bool = False,
    ):
        try:
            from vosk import KaldiRecognizer, Model  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("vosk가 설치되어 있지 않습니다. pip install vosk 로 설치해주세요.") from exc

        # Removed pyttsx3 - using system say command
        self.queue: queue.Queue[bytes] = queue.Queue()
        self.samplerate = samplerate
        self.block_duration = block_duration
        self.blocksize = max(1, int(samplerate * block_duration))
        self.silence_threshold = 600.0
        self.silence_duration = 1.2
        self.max_recording = 12.0
        self.use_keyboard_input = use_keyboard_input
        self.keyboard_controller = KeyboardVoiceInputController(samplerate) if use_keyboard_input else None

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, samplerate)

    def speak(self, text: str):
        global _current_tts_process
        try:
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', text])
        except Exception:
            pass

    def _audio_callback(self, indata, frames, time, status):
        self.queue.put(bytes(indata))

    def listen(self) -> Optional[str]:
        if self.use_keyboard_input and self.keyboard_controller:
            audio_bytes = self.keyboard_controller.record()
        else:
            audio_bytes = self._record_audio()
            
        if not audio_bytes:
            return None
        return self._transcribe(audio_bytes)

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
                        print("🎙️ 음성 감지됨 (녹음 중)")
                    continue

                collected.extend(data)
                if rms > self.silence_threshold:
                    silence_chunks = 0
                else:
                    silence_chunks += 1
                    if silence_chunks >= silence_chunks_required:
                        break

        return bytes(collected) if collected else None

    def _transcribe(self, audio_bytes: bytes) -> Optional[str]:
        try:
            self.recognizer.Reset()
            self.recognizer.AcceptWaveform(audio_bytes)
            result = self.recognizer.Result()
            import json

            text = json.loads(result).get("text", "").strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            print("vosk 음성 인식 실패:", exc)
            return None


class RTZRSpeechInterface:
    """
    RTZR(OpenAPI) 기반 STT/TTS 인터페이스 (gRPC 스트리밍).
    - STT: vito_stt_client_pb2/_grpc 사용
    - TTS: pyttsx3 로 로컬 출력 (RTZR TTS가 필요하면 확장)
    필요한 환경변수:
      RTZR_CLIENT_ID, RTZR_CLIENT_SECRET
    """

    API_BASE = "https://openapi.vito.ai"
    GRPC_SERVER_URL = "grpc-openapi.vito.ai:443"
    SAMPLE_RATE = 16000
    CHUNK = int(SAMPLE_RATE / 10)  # 100ms
    CHANNELS = 1 if sys.platform == "darwin" else 2
    ENCODING = rtzr_pb.DecoderConfig.AudioEncoding.LINEAR16 if rtzr_pb else None

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        samplerate: int = SAMPLE_RATE,
        chunk: int = CHUNK,
        channels: int = CHANNELS,
        use_keyboard_input: bool = False,
    ):
        self.use_keyboard_input = use_keyboard_input
        self.keyboard_controller = KeyboardVoiceInputController(samplerate, channels) if use_keyboard_input else None
        if not rtzr_pb:
            raise ImportError("vito_stt_client_pb2 module not found. Please install generated protobuf files.")
        cfg = load_rtzr_voice_config()
        self.client_id = client_id or cfg["client_id"]
        self.client_secret = client_secret or cfg["client_secret"]
        if not self.client_id or not self.client_secret:
            raise RuntimeError("RTZR_CLIENT_ID/RTZR_CLIENT_SECRET 가 필요합니다. rtzr_voice_env.txt 또는 환경 변수를 확인하세요.")

        self.samplerate = samplerate
        self.chunk = chunk
        self.channels = channels
        # Removed pyttsx3 - using system say command
        self._sess = requests.Session()
        self._token = None
        self._audio = pyaudio.PyAudio()
        self._buffer: queue.Queue[bytes] = queue.Queue()
        self._stream = None

    # --- Token helpers -------------------------------------------------
    @property
    def token(self) -> str:
        if not self._token or self._token.get("expire_at", 0) < time.time():
            resp = self._sess.post(
                f"{self.API_BASE}/v1/authenticate",
                data={"client_id": self.client_id, "client_secret": self.client_secret},
            )
            resp.raise_for_status()
            self._token = resp.json()
        return self._token["access_token"]

    # --- IO helpers ----------------------------------------------------
    def speak(self, text: str):
        global _current_tts_process
        try:
            # Wait for previous TTS to finish
            if _current_tts_process:
                try:
                    _current_tts_process.wait(timeout=30)
                except:
                    pass
            # Start new TTS
            _current_tts_process = subprocess.Popen(['say', text])
        except Exception:
            pass


    def _microphone_stream(self):
        """Generator yielding raw audio bytes from microphone."""
        self._buffer = queue.Queue()

        def _callback(in_data, frame_count, time_info, status):
            self._buffer.put(in_data)
            return (None, pyaudio.paContinue)

        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.samplerate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=_callback,
        )
        self._stream.start_stream()

        try:
            while True:
                chunk = self._buffer.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

    def _decoder_config(self):
        return rtzr_pb.DecoderConfig(
            sample_rate=self.samplerate,
            encoding=self.ENCODING,
            use_itn=True,
            use_disfluency_filter=False,
            use_profanity_filter=False,
            keywords=[],
        )

    def listen(self) -> Optional[str]:
        """Stream audio to RTZR and return a single final transcript."""
        if self.use_keyboard_input and self.keyboard_controller:
            # PTT recording
            audio_bytes = self.keyboard_controller.record()
            if not audio_bytes:
                return None
            
            # For RTZR, we need to stream this audio buffer
            # We can create a generator that yields chunks from audio_bytes
            def _byte_stream():
                offset = 0
                while offset < len(audio_bytes):
                    yield audio_bytes[offset:offset+self.chunk*2] # 2 bytes per sample
                    offset += self.chunk*2

            # Now use the existing gRPC logic but with _byte_stream instead of _microphone_stream
            base_creds = grpc.ssl_channel_credentials()
            call_creds = grpc.access_token_call_credentials(self.token)
            creds = grpc.composite_channel_credentials(base_creds, call_creds)
            
            with grpc.secure_channel(self.GRPC_SERVER_URL, credentials=creds) as channel:
                stub = rtzr_pb_grpc.OnlineDecoderStub(channel)

                def request_iterator():
                    yield rtzr_pb.DecoderRequest(streaming_config=self._decoder_config())
                    for chunk in _byte_stream():
                        yield rtzr_pb.DecoderRequest(audio_content=chunk)

                try:
                    responses = stub.Decode(request_iterator())
                    for resp in responses:
                        for res in resp.results:
                            if res.is_final:
                                return res.alternatives[0].text.strip() or None
                except Exception as exc:
                    print("RTZR PTT 인식 실패:", exc)
                return None

        # Normal microphone streaming
        base_creds = grpc.ssl_channel_credentials()
        call_creds = grpc.access_token_call_credentials(self.token)
        creds = grpc.composite_channel_credentials(base_creds, call_creds)
        with grpc.secure_channel(self.GRPC_SERVER_URL, credentials=creds) as channel:
            stub = rtzr_pb_grpc.OnlineDecoderStub(channel)

            def request_iterator():
                # Send config first
                yield rtzr_pb.DecoderRequest(streaming_config=self._decoder_config())
                # Then audio chunks
                for chunk in self._microphone_stream():
                    yield rtzr_pb.DecoderRequest(audio_content=chunk)

            final_text = None
            try:
                responses = stub.Decode(request_iterator())
                for resp in responses:
                    for res in resp.results:
                        text = res.alternatives[0].text
                        if res.is_final:
                            final_text = text
                            # Stop mic
                            self._buffer.put(None)
                            return final_text.strip() or None
            except Exception as exc:  # noqa: BLE001
                print("RTZR 음성 인식 실패:", exc)
            finally:
                # ensure mic closed
                try:
                    self._buffer.put(None)
                except Exception:
                    pass
            return final_text


def build_io_interface(
    *,
    voice_enabled: bool,
    stt_backend: str = "rtzr",
    use_keyboard_input: bool = False,
):
    if not voice_enabled:
        return TextInterface()

    backend = (stt_backend or "rtzr").lower()

    if backend == "vosk":
        return VoskSpeechInterface(
            use_keyboard_input=use_keyboard_input
            )

    if backend == "rtzr":
        # 새 RTZR gRPC 기반 인터페이스
        return RTZRSpeechInterface(
            use_keyboard_input=use_keyboard_input
        )

    return OpenAIVoiceInterface(
        use_keyboard_input=use_keyboard_input,
    )


def microphone_available() -> bool:
    """Check if an input-capable audio device exists."""
    try:
        devices = sd.query_devices()
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  마이크 장치를 확인하지 못했습니다: {exc}")
        return False

    default_index = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
    has_input_device = False

    # Prefer default input device if valid
    try:
        if default_index is not None and default_index >= 0:
            info = sd.query_devices(default_index)
            if info.get("max_input_channels", 0) > 0:
                print(f"🎧 기본 입력 장치: {info.get('name', 'unknown')}")
                return True
    except Exception:
        pass

    # Fallback: any device with input channels
    for dev in devices:
        if dev.get("max_input_channels", 0) > 0:
            print(f"🎧 사용 가능한 입력 장치 감지: {dev.get('name', 'unknown')}")
            has_input_device = True
            break

    if not has_input_device:
        print("⚠️  입력 가능한 마이크 장치를 찾지 못했습니다.")
    return has_input_device
