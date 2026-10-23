"""Pipeline behaviour with fake adapters (no network)."""

from __future__ import annotations

import pytest

from voice_language.core.errors import EmptyTranscriptError, TranslationTooLongError
from voice_language.core.languages import find_language
from voice_language.core.pipeline import TranslationPipeline


class FakeSTT:
    def __init__(self, text: str = "Hola, ¿qué tal?") -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    def transcribe(self, audio: bytes, *, filename: str, language: str) -> str:
        self.calls.append({"audio": audio, "filename": filename, "language": language})
        return self.text


class FakeTranslator:
    def __init__(self, text: str = "Hi, how are you?") -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    def translate(self, text: str, *, source: object, target: object) -> str:
        self.calls.append({"text": text, "source": source, "target": target})
        return self.text


class FakeTTS:
    def __init__(self, audio: bytes = b"mp3-bytes") -> None:
        self.audio = audio
        self.calls: list[dict[str, object]] = []

    def synthesize(self, text: str, *, language: object, voice: str) -> bytes:
        self.calls.append({"text": text, "language": language, "voice": voice})
        return self.audio


def build_pipeline(stt=None, translator=None, tts=None) -> tuple:
    stt = stt or FakeSTT()
    translator = translator or FakeTranslator()
    tts = tts or FakeTTS()
    return TranslationPipeline(stt, translator, tts), stt, translator, tts


async def test_happy_path_runs_every_stage() -> None:
    pipeline, stt, translator, tts = build_pipeline()
    source = find_language("es")
    target = find_language("en")

    result = await pipeline.run(b"wav", source=source, target=target)

    assert result.transcript == "Hola, ¿qué tal?"
    assert result.translation == "Hi, how are you?"
    assert result.audio == b"mp3-bytes"
    assert set(result.timings_ms) == {"stt", "translation", "tts", "total"}
    assert stt.calls[0]["language"] == "es"
    assert stt.calls[0]["filename"] == "utterance.wav"
    assert translator.calls[0]["source"] == source
    assert tts.calls[0]["voice"] == target.voice


async def test_transcript_and_translation_are_normalised() -> None:
    pipeline, _, _, _ = build_pipeline(
        stt=FakeSTT("  hola \n  mundo  "),
        translator=FakeTranslator('"Hello world"'),
    )

    result = await pipeline.run(b"wav", source=find_language("es"), target=find_language("en"))

    assert result.transcript == "hola mundo"
    assert result.translation == "Hello world"


async def test_empty_audio_is_rejected_before_calling_the_api() -> None:
    pipeline, stt, _, _ = build_pipeline()

    with pytest.raises(EmptyTranscriptError):
        await pipeline.run(b"", source=find_language("es"), target=find_language("en"))

    assert stt.calls == []


async def test_silent_transcription_is_rejected() -> None:
    pipeline, _, translator, _ = build_pipeline(stt=FakeSTT("   "))

    with pytest.raises(EmptyTranscriptError):
        await pipeline.run(b"wav", source=find_language("es"), target=find_language("en"))

    assert translator.calls == []


async def test_speak_false_skips_tts() -> None:
    pipeline, _, _, tts = build_pipeline()

    result = await pipeline.run(
        b"wav", source=find_language("es"), target=find_language("en"), speak=False
    )

    assert result.audio is None
    assert tts.calls == []


async def test_translation_over_the_tts_limit_fails_loudly() -> None:
    pipeline, _, _, tts = build_pipeline(translator=FakeTranslator("x" * 5000))

    with pytest.raises(TranslationTooLongError):
        await pipeline.run(b"wav", source=find_language("es"), target=find_language("en"))

    assert tts.calls == []


async def test_empty_translation_falls_back_to_the_transcript() -> None:
    pipeline, _, _, _ = build_pipeline(translator=FakeTranslator(""))

    result = await pipeline.run(b"wav", source=find_language("es"), target=find_language("en"))

    assert result.translation == result.transcript
