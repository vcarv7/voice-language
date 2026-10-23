"""Ports the pipeline depends on.

Adapters are synchronous on purpose: the pipeline runs them in worker threads
so the Flet event loop never blocks. Swapping OpenAI for a local stack means
writing another object that satisfies these protocols.
"""

from __future__ import annotations

from typing import Protocol

from .models import Language


class SpeechToText(Protocol):
    def transcribe(self, audio: bytes, *, filename: str, language: str) -> str:
        """Return the spoken text contained in ``audio``."""


class Translator(Protocol):
    def translate(self, text: str, *, source: Language, target: Language) -> str:
        """Return ``text`` translated from ``source`` to ``target``."""


class TextToSpeech(Protocol):
    def synthesize(self, text: str, *, language: Language, voice: str) -> bytes:
        """Return encoded audio that reads ``text`` in ``language``."""
