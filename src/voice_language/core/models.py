"""Small, framework-free data structures used across the app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Language:
    """A supported language plus the voice used to speak it."""

    code: str
    name: str
    native: str
    voice: str


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Everything produced by one translation turn."""

    transcript: str
    translation: str
    audio: bytes | None
    timings_ms: dict[str, int]
