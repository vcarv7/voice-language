"""The language catalogue is data, so it gets data tests."""

from __future__ import annotations

from voice_language.core.languages import (
    DEFAULT_SOURCE,
    DEFAULT_TARGET,
    LANGUAGES,
    codes,
    find_language,
    is_supported,
)

ALLOWED_VOICES = {
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
    "marin",
    "cedar",
}


def test_codes_are_unique_and_lowercase() -> None:
    all_codes = codes()
    assert len(all_codes) == len(set(all_codes))
    assert all(code.islower() and len(code) == 2 for code in all_codes)


def test_every_voice_is_supported_by_the_speech_api() -> None:
    assert {language.voice for language in LANGUAGES} <= ALLOWED_VOICES


def test_defaults_exist() -> None:
    assert is_supported(DEFAULT_SOURCE)
    assert is_supported(DEFAULT_TARGET)
    assert DEFAULT_SOURCE != DEFAULT_TARGET


def test_find_language_falls_back_for_unknown_codes() -> None:
    assert find_language("es").code == "es"
    assert find_language("xx").code == DEFAULT_SOURCE


def test_each_language_has_the_display_fields() -> None:
    for language in LANGUAGES:
        assert language.name and language.native
        assert language.name != language.native or language.code == "en"
