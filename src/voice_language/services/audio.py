"""Microphone recording and spoken-output playback."""

from __future__ import annotations

import contextlib
import io
import logging
import shutil
import tempfile
import wave
from pathlib import Path

import flet as ft
import flet_audio as fta
import flet_audio_recorder as far

from ..core.errors import RecordingError

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44_100
MIN_DURATION_S = 0.4


class RecorderService:
    """Wraps flet-audio-recorder and always delivers WAV bytes."""

    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._recorder = far.AudioRecorder(
            configuration=far.AudioRecorderConfiguration(
                encoder=far.AudioEncoder.WAV,
                sample_rate=SAMPLE_RATE,
                channels=1,
                suppress_noise=True,
                cancel_echo=True,
                auto_gain=True,
            )
        )
        page.services.append(self._recorder)
        self._directory: Path | None = None
        self._path: Path | None = None

    async def start(self) -> None:
        try:
            allowed = await self._recorder.has_permission()
        except Exception as exc:  # noqa: BLE001 - plugin/platform specific
            raise RecordingError(f"No se pudo comprobar el permiso del micrófono: {exc}") from exc
        if not allowed:
            raise RecordingError(
                "Permiso de micrófono denegado. Actívalo en los ajustes del sistema."
            )

        self._directory = Path(tempfile.mkdtemp(prefix="voice-language-"))
        self._path = self._directory / "utterance.wav"
        try:
            started = await self._recorder.start_recording(str(self._path))
        except Exception as exc:  # noqa: BLE001
            self._cleanup()
            raise RecordingError(f"No se pudo iniciar la grabación: {exc}") from exc
        if not started:
            self._cleanup()
            raise RecordingError("El micrófono no pudo iniciar la grabación.")

    async def stop(self) -> bytes:
        path = self._path
        try:
            returned = await self._recorder.stop_recording()
        except Exception as exc:  # noqa: BLE001
            self._cleanup()
            raise RecordingError(f"No se pudo detener la grabación: {exc}") from exc

        final_path = Path(returned) if returned else path
        try:
            if final_path is None or not final_path.exists():
                raise RecordingError("No se generó ningún archivo de audio.")
            data = final_path.read_bytes()
        finally:
            self._cleanup()

        duration = wav_duration_s(data)
        if duration < MIN_DURATION_S:
            raise RecordingError("La grabación fue demasiado corta. Mantén pulsado y habla.")
        logger.debug("Recorded %.2f s of audio (%d bytes)", duration, len(data))
        return data

    def _cleanup(self) -> None:
        if self._path is not None:
            with contextlib.suppress(OSError):
                self._path.unlink(missing_ok=True)
        if self._directory is not None:
            shutil.rmtree(self._directory, ignore_errors=True)
        self._path = None
        self._directory = None

    async def diagnostics(self) -> str:
        """Human-readable check of permission, WAV support and input devices."""
        try:
            permission = "concedido" if await self._recorder.has_permission() else "denegado"
        except Exception as exc:  # noqa: BLE001
            permission = f"error ({exc})"
        try:
            wav = await self._recorder.is_supported_encoder(far.AudioEncoder.WAV)
            wav_label = "sí" if wav else "no"
        except Exception as exc:  # noqa: BLE001
            wav_label = f"error ({exc})"
        try:
            devices = await self._recorder.get_input_devices()
            names = ", ".join(device.label or device.id for device in devices) or "ninguno"
        except Exception as exc:  # noqa: BLE001
            names = f"error ({exc})"
        return f"Permiso: {permission} · WAV: {wav_label} · Micrófonos: {names}"


class PlayerService:
    """Plays MP3 bytes through a single reusable flet-audio player."""

    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._audio = fta.Audio(autoplay=False, release_mode=fta.ReleaseMode.RELEASE)
        page.services.append(self._audio)

    async def play(self, data: bytes) -> None:
        if not data:
            return
        with contextlib.suppress(Exception):
            await self._audio.release()
        self._audio.src = data
        self._page.update()
        await self._audio.play()

    async def stop(self) -> None:
        with contextlib.suppress(Exception):
            await self._audio.release()
        self._audio.src = None
        self._page.update()


def wav_duration_s(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as handle:
            rate = handle.getframerate() or SAMPLE_RATE
            return handle.getnframes() / rate
    except (wave.Error, EOFError):
        return 0.0
