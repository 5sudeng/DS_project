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
        text_output_enabled: bool = True,
        voice_output_enabled: bool = False,
        text_input_enabled: bool = True,
        voice_input_enabled: bool = False,
        keyboard_voice: bool = False,
        voice_backend: str = "openai",
        voice_base_url: Optional[str] = None,
        voice_stt_model: Optional[str] = None,
        **kwargs,
    ):
        # We do not forward kwargs since upstream mixins don't expect them.
        super().__init__()

        if voice_input_enabled == text_input_enabled:
            raise ValueError("Exactly one of voice_input_enabled or text_input_enabled must be True.")

        self.text_output_enabled = text_output_enabled
        self.voice_output_enabled = voice_output_enabled
        self.text_input_enabled = text_input_enabled
        self.voice_input_enabled = voice_input_enabled
        self.keyboard_voice = keyboard_voice
        self.voice_backend = voice_backend
        self.voice_base_url = voice_base_url
        self.voice_stt_model = voice_stt_model

        self.io = None
        self._orig_print = None
        self._orig_input = None

        if self.voice_output_enabled or self.voice_input_enabled:
            self.io = build_io_interface(
                voice_enabled=True,
                stt_backend=self.voice_backend,
                stt_model=self.voice_stt_model,
                use_keyboard_input=self.keyboard_voice,
                base_url=self.voice_base_url,
            )

    def _io_output(self, msg: str):
        """Route output through configured text/voice channels."""
        text_printer = self._orig_print if getattr(self, "_orig_print", None) else print
        if self.text_output_enabled:
            text_printer(msg)
        if self.voice_output_enabled and self.io:
            try:
                self.io.speak(msg)
            except Exception:
                pass

    async def run(self):  # type: ignore[override]
        """Patch print/input according to IO configuration then run CLI loop."""
        def _status(msg: str):
            if self.text_output_enabled:
                print(msg)

        # Handle voice input pre-checks
        if self.voice_input_enabled:
            mic_ok = microphone_available()
            if not mic_ok:
                _status("⚠️  마이크를 감지하지 못했습니다.")
                if self.keyboard_voice:
                    _status("⌨️  키보드 푸시투토크 모드로 진행합니다.")
                else:
                    _status("✏️  텍스트 입력으로 전환합니다.")
                    self.voice_input_enabled = False
                    self.text_input_enabled = True

        if self.voice_output_enabled and self.text_output_enabled:
            _status("🔊 음성 출력 + 텍스트 출력 활성화.")
        elif self.voice_output_enabled:
            _status("🔊 음성 출력만 활성화.")
        elif self.text_output_enabled:
            _status("✏️  텍스트 출력만 활성화.")

        # Patch print/input
        self._orig_print = builtins.print
        self._orig_input = builtins.input

        def _patched_print(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            if self.text_output_enabled:
                self._orig_print(*args, **kwargs)

        def _patched_input(prompt: str = "") -> str:
            prompt_str = prompt or ""
            if self.voice_output_enabled and prompt_str and self.io:
                try:
                    self.io.speak(prompt_str)
                except Exception:
                    pass

            if self.voice_input_enabled and self.io:
                attempt = 0
                max_attempts = 3
                while attempt < max_attempts:
                    if self.text_output_enabled:
                        self._orig_print("🎤 음성 입력 대기 중...")
                    heard = self.io.listen()
                    if heard:
                        if self.text_output_enabled:
                            self._orig_print(f"[Voice 입력] {heard}")
                        return heard
                    attempt += 1
                    if attempt < max_attempts and self.text_output_enabled:
                        self._orig_print("🔁 음성이 감지되지 않았습니다. 다시 말씀해주세요.")
                if self.keyboard_voice and self.text_output_enabled:
                    return self._orig_input(prompt)
                return ""

            if self.text_input_enabled:
                return self._orig_input(prompt)

            return ""

        builtins.print = _patched_print
        builtins.input = _patched_input

        try:
            await self._run_cli()
        finally:
            builtins.print = self._orig_print or print
            builtins.input = self._orig_input or input


class TextIOMixin(IOMixin):
    """Text-only IO defaults."""

    def __init__(self, *, text_output_enabled: bool = True, text_input_enabled: bool = True, **kwargs):
        super().__init__(
            text_output_enabled=text_output_enabled,
            voice_output_enabled=False,
            text_input_enabled=text_input_enabled,
            voice_input_enabled=False,
            keyboard_voice=False,
            **kwargs,
        )


class VoiceIOMixin(IOMixin):
    """Voice-first IO defaults (voice input; text output optional)."""

    def __init__(
        self,
        *,
        voice_output_enabled: bool = True,
        text_output_enabled: bool = True,
        voice_input_enabled: bool = True,
        keyboard_voice: bool = False,
        voice_backend: str = "rtzr",
        voice_base_url: Optional[str] = None,
        voice_stt_model: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            text_output_enabled=text_output_enabled,
            voice_output_enabled=voice_output_enabled,
            text_input_enabled=not voice_input_enabled,
            voice_input_enabled=voice_input_enabled,
            keyboard_voice=keyboard_voice,
            voice_backend=voice_backend,
            voice_base_url=voice_base_url,
            voice_stt_model=voice_stt_model,
            **kwargs,
        )
