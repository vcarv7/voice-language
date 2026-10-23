"""End-to-end check of the OpenAI chain without touching the UI.

Requires OPENAI_API_KEY in the environment (never hardcode it):

    $env:OPENAI_API_KEY = "sk-..."
    uv run python scripts/smoke_api.py

The script synthesises a Spanish sentence, transcribes it, translates it to
English, synthesises the translation and then translates it back to Spanish.
That exercises STT, MT and TTS in both directions.
"""

from __future__ import annotations

import asyncio
import os
import sys

from voice_language.adapters.openai_engine import OpenAIEngine
from voice_language.core.languages import find_language
from voice_language.core.pipeline import TranslationPipeline

SENTENCE = "Hola, me llamo Víctor y estoy probando el traductor de voz."


async def run() -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Missing OPENAI_API_KEY in the environment.")
        return 1

    engine = OpenAIEngine(api_key)
    spanish = find_language("es")
    english = find_language("en")

    print(f"1/4 Synthesising Spanish input ({spanish.voice})...")
    audio = await asyncio.to_thread(
        engine.synthesize, SENTENCE, language=spanish, voice=spanish.voice
    )
    print(f"    {len(audio)} bytes of MP3")

    pipeline = TranslationPipeline(engine, engine, engine)

    print("2/4 Transcribing + translating to English + speaking...")
    forward = await pipeline.run(audio, source=spanish, target=english)
    print(f"    transcript : {forward.transcript}")
    print(f"    translation: {forward.translation}")
    print(f"    audio      : {len(forward.audio or b'')} bytes")
    print(f"    timings    : {forward.timings_ms}")

    print("3/4 Translating the English audio back to Spanish...")
    backward = await pipeline.run(forward.audio or b"", source=english, target=spanish)
    print(f"    transcript : {backward.transcript}")
    print(f"    translation: {backward.translation}")
    print(f"    timings    : {backward.timings_ms}")

    print("4/4 OK: both directions work.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(run()))
