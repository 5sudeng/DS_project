"""Mixins to control text/voice IO routing for the CLI."""

from __future__ import annotations

import builtins
from typing import Optional

from core.voice_io import build_io_interface, microphone_available


class IOMixin:
    """Base IO mixin that patches print/input based on configured channels."""

    def __init__(
        self,
        *,
        keyboard_voice: bool = False,
        voice_backend: str = "rtzr",
        output_mode: str = "both",
        input_mode: str = "voice",
    ):
        # We do not forward kwargs since upstream mixins don't expect them.
        super().__init__()

        self.io = None
        self._orig_print = builtins.print
        self._orig_input = builtins.input

        self.keyboard_voice = keyboard_voice
        self.voice_backend = voice_backend
        self.output_mode = output_mode.lower()
        self.input_mode = input_mode.lower()

        if self.output_mode in ("voice", "both") or self.input_mode == "voice":
            self.io = build_io_interface(
                voice_enabled=True,
                stt_backend=self.voice_backend,
                use_keyboard_input=self.keyboard_voice,
            )

    def io_output(self, msg: str):
        """Public helper to emit user-facing output based on output mode."""
        # When we expect immediate voice input, wait for TTS to finish to avoid feedback.
        wait_for_tts = self.input_mode == "voice"
        if self.output_mode in ("text", "both"):
            self.console_print(msg)
        if self.output_mode in ("voice", "both") and self.io:
            try:
                self.io.speak(msg, wait=wait_for_tts)
            except Exception:
                pass

    def console_print(self, *args, **kwargs):
        """Always print to console regardless of output mode."""
        self._orig_print(*args, **kwargs)

    def io_input(self) -> Optional[str]:
        """Unified input that respects input/output configuration."""
        # Handle input
        if self.input_mode == "voice" and self.io:
            attempt = 0
            max_attempts = 3
            while attempt < max_attempts:
                if self.output_mode in ("text", "both"):
                    self.console_print("🎤 음성 입력 대기중...")
                heard = self.io.listen()
                if heard:
                    if self.output_mode in ("text", "both"):
                        self.console_print(f"[Voice 입력] {heard}")
                    return heard
                attempt += 1
                if attempt < max_attempts and self.output_mode in ("text", "both"):
                    self.console_print("🎤 음성을 감지하지 못했습니다. 다시 말씀해주세요.")
            if self.keyboard_voice and self.output_mode in ("text", "both"):
                try:
                    return self._orig_input()
                except EOFError:
                    return ""
            return ""

        if self.input_mode == "text":
            try:
                return self._orig_input()
            except EOFError:
                return ""

        return ""

    @classmethod
    def add_io_arguments(cls, parser):
        """Register IO-related CLI arguments."""
        parser.add_argument("--input-mode", choices=["text", "voice"], default="voice", help="입력 모드 선택")
        parser.add_argument(
            "--output-mode",
            choices=["text", "voice", "both"],
            default="both",
            help="출력 모드 선택 (텍스트/음성/둘다)",
        )
        parser.add_argument(
            "--keyboard-voice",
            action="store_true",
            help="음성 입력 실패 시 폴백으로 키보드 모드 활용",
        )
        parser.add_argument(
            "--stt-backend",
            choices=["openai", "rtzr"],
            default="rtzr",
            help="음성 인식 백엔드 선택",
        )

    def setup_io_patching(self):
        """Setup IO configuration and patch input builtin."""
        # Handle voice input pre-checks
        if self.input_mode == "voice":
            mic_ok = microphone_available()
            if not mic_ok:
                self.console_print("⚠️  마이크를 감지하지 못했습니다.")
                if self.keyboard_voice:
                    self.console_print("⚠️  폴백으로 키보드 모드로 진행합니다.")
                else:
                    self.console_print("⚠️  텍스트 입력으로 전환합니다.")
                    self.input_mode = "text"

        if self.output_mode == "both":
            self.io_output("🔊 음성 출력 + 텍스트 출력 활성화")
        elif self.output_mode == "voice":
            self.io_output("🔊 음성 출력만 활성화")
        elif self.output_mode == "text":
            self.io_output("📝 텍스트 출력만 활성화")
