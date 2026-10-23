"""Supported languages and the TTS voice assigned to each one.

Voice names are validated against the OpenAI speech API. Voices are
multilingual, so the assignment is mostly a matter of giving each language a
distinct, recognisable voice during a conversation.
"""

from __future__ import annotations

from .models import Language

LANGUAGES: tuple[Language, ...] = (
    Language("es", "Spanish", "Español", "marin"),
    Language("en", "English", "English", "nova"),
    Language("fr", "French", "Français", "coral"),
    Language("de", "German", "Deutsch", "onyx"),
    Language("it", "Italian", "Italiano", "alloy"),
    Language("pt", "Portuguese", "Português", "shimmer"),
    Language("nl", "Dutch", "Nederlands", "ballad"),
    Language("ru", "Russian", "Русский", "ash"),
    Language("ar", "Arabic", "العربية", "cedar"),
    Language("hi", "Hindi", "हिन्दी", "fable"),
    Language("ja", "Japanese", "日本語", "sage"),
    Language("zh", "Chinese", "中文", "verse"),
)

DEFAULT_SOURCE = "es"
DEFAULT_TARGET = "en"

_BY_CODE = {language.code: language for language in LANGUAGES}


def find_language(code: str, fallback: str = DEFAULT_SOURCE) -> Language:
    """Return the language for ``code`` or the fallback when unknown."""
    return _BY_CODE.get(code) or _BY_CODE.get(fallback) or LANGUAGES[0]


def is_supported(code: str) -> bool:
    return code in _BY_CODE


def codes() -> tuple[str, ...]:
    return tuple(language.code for language in LANGUAGES)
