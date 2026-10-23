"""Persisted user settings.

The API key is stored in the user's config directory, never in the repository.
For a locally run desktop app that is an acceptable trade-off; see README for
the keyring hardening path.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import platformdirs

from ..core.languages import DEFAULT_SOURCE, DEFAULT_TARGET

logger = logging.getLogger(__name__)

APP_NAME = "voice-language"
APP_AUTHOR = "vcarv7"


@dataclass(slots=True)
class Settings:
    api_key: str = ""
    source: str = DEFAULT_SOURCE
    target: str = DEFAULT_TARGET
    speak: bool = True
    autoplay: bool = True
    stt_model: str = "gpt-4o-mini-transcribe"
    translation_model: str = "gpt-4o-mini"
    tts_model: str = "gpt-4o-mini-tts"


def settings_path() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR)) / "settings.json"


def load_settings() -> Settings:
    settings = Settings()
    path = settings_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            known = {field.name for field in fields(Settings)}
            settings = Settings(**{k: v for k, v in payload.items() if k in known})
        except (OSError, ValueError, TypeError):
            logger.warning("Ignoring unreadable settings file at %s", path)
    return settings


def env_api_key() -> str:
    """Key supplied through the environment, useful for development."""
    return os.environ.get("OPENAI_API_KEY", "").strip()


def effective_api_key(settings: Settings) -> str:
    return (settings.api_key or env_api_key()).strip()


def save_settings(settings: Settings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
