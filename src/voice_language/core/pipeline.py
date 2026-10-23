"""Speech -> text -> translation -> speech orchestration."""

from __future__ import annotations

import asyncio
import time

from .errors import EmptyTranscriptError, TranslationTooLongError
from .models import Language, PipelineResult
from .ports import SpeechToText, TextToSpeech, Translator

MAX_TTS_CHARS = 4096


class TranslationPipeline:
    """One conversation turn, with per-stage timings for the UI."""

    def __init__(
        self,
        speech_to_text: SpeechToText,
        translator: Translator,
        text_to_speech: TextToSpeech,
    ) -> None:
        self._stt = speech_to_text
        self._translator = translator
        self._tts = text_to_speech

    async def run(
        self,
        audio: bytes,
        *,
        source: Language,
        target: Language,
        speak: bool = True,
    ) -> PipelineResult:
        if not audio:
            raise EmptyTranscriptError()

        started = time.perf_counter()
        transcript = await asyncio.to_thread(
            self._stt.transcribe,
            audio,
            filename="utterance.wav",
            language=source.code,
        )
        transcript = _clean(transcript)
        if not transcript:
            raise EmptyTranscriptError()

        transcribed_at = time.perf_counter()
        translation = await asyncio.to_thread(
            self._translator.translate,
            transcript,
            source=source,
            target=target,
        )
        translation = _clean(translation) or transcript

        translated_at = time.perf_counter()
        spoken: bytes | None = None
        if speak:
            if len(translation) > MAX_TTS_CHARS:
                raise TranslationTooLongError(len(translation), MAX_TTS_CHARS)
            spoken = await asyncio.to_thread(
                self._tts.synthesize,
                translation,
                language=target,
                voice=target.voice,
            )

        finished = time.perf_counter()
        return PipelineResult(
            transcript=transcript,
            translation=translation,
            audio=spoken,
            timings_ms={
                "stt": _ms(transcribed_at - started),
                "translation": _ms(translated_at - transcribed_at),
                "tts": _ms(finished - translated_at),
                "total": _ms(finished - started),
            },
        )


def _clean(text: str) -> str:
    """Collapse whitespace and drop the quotes models like to add."""
    cleaned = " ".join(text.split())
    for left, right in (('"', '"'), ("“", "”"), ("'", "'")):
        if len(cleaned) > 1 and cleaned.startswith(left) and cleaned.endswith(right):
            cleaned = cleaned[1:-1].strip()
            break
    return cleaned


def _ms(seconds: float) -> int:
    return max(0, round(seconds * 1000))
