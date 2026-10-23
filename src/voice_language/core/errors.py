"""Errors whose message is safe to show to the user."""

from __future__ import annotations


class VoiceLanguageError(Exception):
    """Base class for expected, user-facing failures."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MissingApiKeyError(VoiceLanguageError):
    def __init__(self) -> None:
        super().__init__("Falta la API key de OpenAI. Ábrela en Ajustes para empezar.")


class EmptyTranscriptError(VoiceLanguageError):
    def __init__(self) -> None:
        super().__init__(
            "No se detectó voz en la grabación. Habla más cerca del micrófono e inténtalo de nuevo."
        )


class RecordingError(VoiceLanguageError):
    pass


class TranslationTooLongError(VoiceLanguageError):
    def __init__(self, length: int, limit: int) -> None:
        super().__init__(
            f"La traducción tiene {length} caracteres y el límite de voz es {limit}. "
            "Divide la frase en partes más cortas."
        )


class ProviderError(VoiceLanguageError):
    """The remote provider rejected or failed a request."""
