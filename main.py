#!/usr/bin/env python3
"""
Main entry point for the Coupang Shopping Assistant.
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from interface.cli import ShoppingCLI

async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Interactive shopping assistant with AI")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--cookie-file", help="Path to cookie file for authentication")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument(
        "--run-dir",
        help="Root directory to store collected product data (default: outputs/scenario_runs)",
    )
    parser.add_argument(
        "--ocr-delay",
        type=float,
        default=0.5,
        help="OCR API 호출 사이 대기 시간(초)",
    )
    parser.add_argument("--voice", action="store_true", help="Enable voice input/output")
    parser.add_argument("--no-visual", action="store_true", help="Disable visual/text output (voice-only)")
    parser.add_argument(
        "--voice-backend",
        choices=["openai", "vosk", "rtzr"],
        default="rtzr",
        help="Select STT backend: openai whisper API, local vosk, or RTZR",
    )
    parser.add_argument(
        "--text-input",
        action="store_true",
        help="Disable STT and use keyboard/text input while keeping voice output",
    )
    parser.add_argument(
        "--keyboard-voice",
        action="store_true",
        help="Push-to-talk style voice capture triggered by the Enter key",
    )
    parser.add_argument(
        "--stt-model",
        help="STT model name (for openai backend)",
    )
    parser.add_argument(
        "--rtzr-client-id",
        default="MZdY1Ll2VlnN2OahP7h1",
        help="RTZR CLIENT_ID (env RTZR_CLIENT_ID 로도 설정 가능)",
    )
    parser.add_argument(
        "--rtzr-client-secret",
        default="Fiey1zKUa5bw3IuOwUj0eoyyiEE8bYkDIhbe_PFf",
        help="RTZR CLIENT_SECRET (env RTZR_CLIENT_SECRET 로도 설정 가능)",
    )
    parser.add_argument(
        "--ai-memory",
        action="store_true",
        help="Enable AI memory based prompt augmentation and re-query",
    )

    args = parser.parse_args()

    # Load API Key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        secret_file = Path(".secret")
        if secret_file.exists():
            api_key = secret_file.read_text().strip()

    if not api_key:
        ### check
        print("Error: OpenAI API Key is required.") 
        ### check
        print("Please provide it via --api-key, OPENAI_API_KEY env var, or .secret file.")
        sys.exit(1)

    cli = ShoppingCLI(
        headless=args.headless,
        cookie_file=args.cookie_file,
        api_key=api_key,
        run_dir=args.run_dir,
        ocr_delay=args.ocr_delay,
        voice_enabled=args.voice,
        visual_enabled=not args.no_visual,
        voice_backend=args.voice_backend,
        keyboard_voice=args.keyboard_voice,
        stt_model=args.stt_model,
        voice_input_enabled=not args.text_input,
        rtzr_client_id=args.rtzr_client_id,
        rtzr_client_secret=args.rtzr_client_secret,
        ai_memory_enabled=args.ai_memory,
    )

    await cli.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ### TODO
        print("\n👋 종료합니다.")
