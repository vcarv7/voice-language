"""Settings persistence and audio helpers."""

from __future__ import annotations

import io
import wave

import platformdirs

from voice_language.services import settings as settings_module
from voice_language.services.audio import wav_duration_s
from voice_language.services.settings import (
    Settings,
    effective_api_key,
    env_api_key,
    load_settings,
    save_settings,
)


def test_settings_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda *a, **k: str(tmp_path))

    original = Settings(
        api_key="sk-test",
        source="es",
        target="ja",
        speak=False,
        autoplay=False,
        stt_model="stt",
        translation_model="mt",
        tts_model="tts",
    )
    save_settings(original)

    assert settings_module.settings_path().exists()
    assert load_settings() == original


def test_unknown_keys_are_ignored(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda *a, **k: str(tmp_path))
    path = settings_module.settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"source": "fr", "legacy": true}', encoding="utf-8")

    settings = load_settings()

    assert settings.source == "fr"
    assert not hasattr(settings, "legacy")


def test_environment_key_is_used_only_as_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert env_api_key() == "sk-env"
    assert effective_api_key(Settings()) == "sk-env"
    assert effective_api_key(Settings(api_key="sk-file")) == "sk-file"


def test_wav_duration() -> None:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(44_100)
        handle.writeframes(b"\x00\x00" * 44_100)
    assert wav_duration_s(buffer.getvalue()) == 1.0


def test_invalid_wav_has_zero_duration() -> None:
    assert wav_duration_s(b"not a wav") == 0.0
