"""Main screen: two language panels, two microphones, one conversation."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Literal

import flet as ft

from ..adapters.openai_engine import OpenAIEngine
from ..core.errors import VoiceLanguageError
from ..core.languages import (
    DEFAULT_SOURCE,
    DEFAULT_TARGET,
    LANGUAGES,
    find_language,
)
from ..core.models import Language
from ..core.pipeline import TranslationPipeline
from ..services.audio import PlayerService, RecorderService
from ..services.settings import (
    Settings,
    effective_api_key,
    env_api_key,
    save_settings,
)

logger = logging.getLogger(__name__)

Direction = Literal["left", "right"]
MAX_RECORDING_SECONDS = 60


class HomeView:
    def __init__(self, page: ft.Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings
        self.recorder = RecorderService(page)
        self.player = PlayerService(page)

        self.engine: OpenAIEngine | None = None
        self.pipeline: TranslationPipeline | None = None

        self._busy = False
        self._recording: Direction | None = None
        self._started_at = 0.0
        self._last_audio: dict[Direction, bytes | None] = {"left": None, "right": None}

        self._source_lang = find_language(settings.source, DEFAULT_SOURCE)
        self._target_lang = find_language(settings.target, DEFAULT_TARGET)
        self._previous_source = self._source_lang.code
        self._previous_target = self._target_lang.code

        self._build_controls()
        self._load_engine()
        self._apply_languages(clear=True)

    # ------------------------------------------------------------------ layout

    def _build_controls(self) -> None:
        self.source_dd = ft.Dropdown(
            label="Idioma A",
            value=self._source_lang.code,
            width=230,
            options=self._language_options(),
            on_select=self._on_source_select,
        )
        self.target_dd = ft.Dropdown(
            label="Idioma B",
            value=self._target_lang.code,
            width=230,
            options=self._language_options(),
            on_select=self._on_target_select,
        )
        self.swap_btn = ft.IconButton(
            icon=ft.Icons.SWAP_HORIZ,
            tooltip="Intercambiar idiomas",
            on_click=self._on_swap,
        )

        self.left_lang = ft.Text(size=15, weight=ft.FontWeight.BOLD)
        self.right_lang = ft.Text(size=15, weight=ft.FontWeight.BOLD)
        self.left_text = ft.Text(size=16, selectable=True)
        self.right_text = ft.Text(size=16, selectable=True)

        self.left_play = ft.IconButton(
            icon=ft.Icons.REPLAY,
            tooltip="Reproducir otra vez",
            data="left",
            on_click=self._on_replay,
            disabled=True,
        )
        self.right_play = ft.IconButton(
            icon=ft.Icons.REPLAY,
            tooltip="Reproducir otra vez",
            data="right",
            on_click=self._on_replay,
            disabled=True,
        )

        self.left_mic = ft.FilledButton(
            "Hablar",
            icon=ft.Icons.MIC,
            data="left",
            on_click=self._on_mic_click,
            height=46,
        )
        self.right_mic = ft.FilledButton(
            "Hablar",
            icon=ft.Icons.MIC,
            data="right",
            on_click=self._on_mic_click,
            height=46,
        )

        self._spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        self._status_text = ft.Text(size=13, color=ft.Colors.ON_SURFACE_VARIANT)

        self.banner = ft.Container(
            visible=False,
            padding=12,
            border_radius=12,
            bgcolor=ft.Colors.ERROR_CONTAINER,
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.KEY, size=18),
                    ft.Text("Añade tu API key de OpenAI para activar el micrófono."),
                    ft.Container(expand=True),
                    ft.TextButton("Abrir ajustes", on_click=self._open_settings),
                ],
            ),
        )

        self._settings_dialog = self._build_settings_dialog()

        header = ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Voice Language", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Habla en un idioma y escucha la traducción. Después, al revés.",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Ajustes",
                    on_click=self._open_settings,
                ),
            ],
        )

        languages = ft.Row(
            controls=[self.source_dd, self.swap_btn, self.target_dd],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=14,
        )

        status = ft.Row(
            controls=[self._spinner, self._status_text],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

        panels = ft.ResponsiveRow(
            controls=[
                self._panel(self.left_lang, self.left_text, self.left_mic, self.left_play),
                self._panel(self.right_lang, self.right_text, self.right_mic, self.right_play),
            ],
            spacing=16,
            run_spacing=16,
        )

        footer = ft.Text(
            f"Máximo {MAX_RECORDING_SECONDS} s por turno · El audio se envía a la API de OpenAI.",
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        self._root = ft.Column(
            controls=[header, self.banner, languages, status, panels, footer],
            spacing=16,
            expand=True,
        )

    def _panel(
        self,
        language: ft.Text,
        transcript: ft.Text,
        mic: ft.FilledButton,
        replay: ft.IconButton,
    ) -> ft.Container:
        return ft.Container(
            col={"sm": 12, "md": 6},
            height=320,
            padding=20,
            border_radius=18,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    language,
                                    ft.Text(
                                        "micrófono",
                                        size=11,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                                spacing=0,
                                expand=True,
                            ),
                            replay,
                        ],
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[transcript],
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                        expand=True,
                        padding=ft.Padding(top=8, bottom=8),
                    ),
                    mic,
                ],
                spacing=10,
                expand=True,
            ),
        )

    def _build_settings_dialog(self) -> ft.AlertDialog:
        self.api_key_field = ft.TextField(
            label="OpenAI API key",
            password=True,
            can_reveal_password=True,
            hint_text="sk-...",
        )
        self.speak_switch = ft.Switch(
            label="Generar la voz de la traducción", value=self.settings.speak
        )
        self.autoplay_switch = ft.Switch(
            label="Reproducirla automáticamente", value=self.settings.autoplay
        )
        self.stt_field = ft.TextField(
            label="Modelo de transcripción", value=self.settings.stt_model
        )
        self.translation_field = ft.TextField(
            label="Modelo de traducción", value=self.settings.translation_model
        )
        self.tts_field = ft.TextField(label="Modelo de voz", value=self.settings.tts_model)
        self.diag_text = ft.Text(size=11, color=ft.Colors.ON_SURFACE_VARIANT)

        return ft.AlertDialog(
            modal=True,
            title=ft.Text("Ajustes"),
            content=ft.Container(
                width=460,
                content=ft.Column(
                    controls=[
                        self.api_key_field,
                        ft.Text(
                            "La key se guarda en tu carpeta de configuración, "
                            "nunca en el proyecto.",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Divider(),
                        self.speak_switch,
                        self.autoplay_switch,
                        ft.Row(
                            controls=[
                                ft.TextButton("Probar micrófono", on_click=self._check_microphone),
                            ]
                        ),
                        self.diag_text,
                        ft.Divider(),
                        ft.Text(
                            "Modelos (cámbialos si OpenAI renombra alguno)",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                        self.stt_field,
                        self.translation_field,
                        self.tts_field,
                    ],
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._close_settings),
                ft.FilledButton("Guardar", on_click=self._save_settings),
            ],
        )

    def mount(self) -> None:
        self.page.add(self._root)
        self._refresh_controls()

    # ------------------------------------------------------------------ engine

    def _load_engine(self) -> None:
        key = effective_api_key(self.settings)
        self.engine = None
        self.pipeline = None
        if not key:
            self.banner.visible = True
            return
        try:
            self.engine = OpenAIEngine(
                key,
                stt_model=self.settings.stt_model,
                translation_model=self.settings.translation_model,
                tts_model=self.settings.tts_model,
            )
        except VoiceLanguageError as exc:
            self.banner.visible = True
            logger.warning("Could not build the OpenAI engine: %s", exc.message)
            return
        self.pipeline = TranslationPipeline(self.engine, self.engine, self.engine)
        self.banner.visible = False

    # --------------------------------------------------------------- recording

    async def _on_mic_click(self, e: ft.Event[ft.FilledButton]) -> None:
        direction: Direction = e.control.data
        if self._recording == direction:
            await self._finish_recording()
        elif self._recording is None and not self._busy:
            await self._start_recording(direction)

    async def _start_recording(self, direction: Direction) -> None:
        try:
            await self.recorder.start()
        except VoiceLanguageError as exc:
            self._toast(exc.message)
            return
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected recorder failure")
            self._toast("No se pudo acceder al micrófono.")
            return

        self._recording = direction
        self._started_at = time.monotonic()
        self._set_status("Grabando… 0 s", spinner=True)
        self._refresh_controls()
        self.page.run_task(self._recording_clock)

    async def _recording_clock(self) -> None:
        while self._recording is not None:
            elapsed = time.monotonic() - self._started_at
            if elapsed >= MAX_RECORDING_SECONDS:
                await self._finish_recording()
                return
            self._status_text.value = f"Grabando… {int(elapsed)} s"
            self._safe_update()
            await asyncio.sleep(0.25)

    async def _finish_recording(self) -> None:
        if self._recording is None:
            return
        direction = self._recording
        self._recording = None
        self._busy = True
        self._set_status("Procesando…", spinner=True)
        self._refresh_controls()

        result = None
        error: str | None = None
        try:
            audio = await self.recorder.stop()
            if self.pipeline is None:
                raise VoiceLanguageError("Configura tu API key antes de grabar.")
            source, target = self._direction_languages(direction)
            result = await self.pipeline.run(
                audio,
                source=source,
                target=target,
                speak=self.settings.speak,
            )
        except VoiceLanguageError as exc:
            error = exc.message
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected failure while processing a turn")
            error = "Fallo inesperado al procesar el audio. Revisa la consola."
        finally:
            self._busy = False
            self._spinner.visible = False

        if error is not None or result is None:
            self._status_text.value = "Sin resultado"
            self._toast(error or "No se pudo procesar el turno.")
            self._refresh_controls()
            return

        if direction == "left":
            self.left_text.value = result.transcript
            self.right_text.value = result.translation
            self._last_audio["right"] = result.audio
        else:
            self.right_text.value = result.transcript
            self.left_text.value = result.translation
            self._last_audio["left"] = result.audio

        timings = result.timings_ms
        self._status_text.value = (
            f"Listo · {timings['total'] / 1000:.1f} s "
            f"(texto {timings['stt']} ms · traducción {timings['translation']} ms · "
            f"voz {timings['tts']} ms)"
        )
        self._refresh_controls()

        if self.settings.autoplay and result.audio:
            try:
                await self.player.play(result.audio)
            except Exception:  # noqa: BLE001
                logger.exception("Could not play the synthesized audio")
                self._toast("El audio se generó pero no se pudo reproducir.")

    def _direction_languages(self, direction: Direction) -> tuple[Language, Language]:
        if direction == "left":
            return self._source_lang, self._target_lang
        return self._target_lang, self._source_lang

    async def _on_replay(self, e: ft.Event[ft.IconButton]) -> None:
        direction: Direction = e.control.data
        data = self._last_audio.get(direction)
        if not data:
            return
        try:
            await self.player.play(data)
        except Exception:  # noqa: BLE001
            logger.exception("Could not replay audio")
            self._toast("No se pudo reproducir el audio.")

    # ---------------------------------------------------------------- languages

    def _language_options(self) -> list[ft.DropdownOption]:
        return [
            ft.DropdownOption(key=language.code, text=f"{language.native} ({language.code})")
            for language in LANGUAGES
        ]

    def _on_source_select(self, e: ft.Event[ft.Dropdown]) -> None:
        if self._recording is not None or self._busy:
            self.source_dd.value = self._source_lang.code
            self._refresh_controls()
            return
        chosen = find_language(self.source_dd.value or DEFAULT_SOURCE, DEFAULT_SOURCE)
        if chosen.code == self._target_lang.code:
            self.target_dd.value = self._previous_source
            self._target_lang = find_language(self._previous_source)
        self._previous_source = chosen.code
        self._source_lang = chosen
        self._apply_languages(clear=True)

    def _on_target_select(self, e: ft.Event[ft.Dropdown]) -> None:
        if self._recording is not None or self._busy:
            self.target_dd.value = self._target_lang.code
            self._refresh_controls()
            return
        chosen = find_language(self.target_dd.value or DEFAULT_TARGET, DEFAULT_TARGET)
        if chosen.code == self._source_lang.code:
            self.source_dd.value = self._previous_target
            self._source_lang = find_language(self._previous_target)
        self._previous_target = chosen.code
        self._target_lang = chosen
        self._apply_languages(clear=True)

    def _on_swap(self, e: ft.Event[ft.IconButton]) -> None:
        if self._recording is not None or self._busy:
            return
        self._source_lang, self._target_lang = self._target_lang, self._source_lang
        self.source_dd.value = self._source_lang.code
        self.target_dd.value = self._target_lang.code
        self._previous_source = self._source_lang.code
        self._previous_target = self._target_lang.code
        self._apply_languages(clear=True)

    def _apply_languages(self, *, clear: bool) -> None:
        self.settings.source = self._source_lang.code
        self.settings.target = self._target_lang.code
        self.source_dd.value = self._source_lang.code
        self.target_dd.value = self._target_lang.code
        self.left_lang.value = f"{self._source_lang.native} · voz {self._source_lang.voice}"
        self.right_lang.value = f"{self._target_lang.native} · voz {self._target_lang.voice}"
        if clear:
            self.left_text.value = "—"
            self.right_text.value = "—"
            self._last_audio = {"left": None, "right": None}
            self._status_text.value = "Listo. Pulsa Hablar en el panel que quieras."
        try:
            save_settings(self.settings)
        except OSError:
            logger.warning("Could not persist the language selection", exc_info=True)
        self._refresh_controls()

    # ------------------------------------------------------------------ status

    def _refresh_controls(self) -> None:
        has_key = bool(effective_api_key(self.settings))
        idle = not self._busy and self._recording is None

        self.left_mic.disabled = not (
            has_key and not self._busy and self._recording in (None, "left")
        )
        self.right_mic.disabled = not (
            has_key and not self._busy and self._recording in (None, "right")
        )
        self.left_mic.content = (
            "Detener" if self._recording == "left" else f"Hablar en {self._source_lang.native}"
        )
        self.right_mic.content = (
            "Detener" if self._recording == "right" else f"Hablar en {self._target_lang.native}"
        )
        left_icon = ft.Icons.STOP if self._recording == "left" else ft.Icons.MIC
        right_icon = ft.Icons.STOP if self._recording == "right" else ft.Icons.MIC
        self.left_mic.icon = left_icon
        self.right_mic.icon = right_icon

        self.left_play.disabled = self._last_audio["left"] is None or self._busy
        self.right_play.disabled = self._last_audio["right"] is None or self._busy
        self.source_dd.disabled = not idle
        self.target_dd.disabled = not idle
        self.swap_btn.disabled = not idle
        self.banner.visible = not has_key

        self._safe_update()

    def _set_status(self, text: str, *, spinner: bool = False) -> None:
        self._status_text.value = text
        self._spinner.visible = spinner
        self._safe_update()

    def _safe_update(self) -> None:
        with contextlib.suppress(Exception):
            self.page.update()

    def _toast(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(content=message, duration=ft.Duration(seconds=5)))

    # ----------------------------------------------------------------- settings

    def _open_settings(self, e: ft.Event | None = None) -> None:
        self.api_key_field.value = self.settings.api_key
        self.api_key_field.error_text = None
        if not self.settings.api_key and env_api_key():
            self.api_key_field.hint_text = "Usando OPENAI_API_KEY del entorno"
        self.speak_switch.value = self.settings.speak
        self.autoplay_switch.value = self.settings.autoplay
        self.stt_field.value = self.settings.stt_model
        self.translation_field.value = self.settings.translation_model
        self.tts_field.value = self.settings.tts_model
        self.page.show_dialog(self._settings_dialog)

    def _close_settings(self, e: ft.Event | None = None) -> None:
        self.page.pop_dialog()

    async def _check_microphone(self, e: ft.Event | None = None) -> None:
        self.diag_text.value = "Comprobando micrófono…"
        self.page.update()
        self.diag_text.value = await self.recorder.diagnostics()
        self.page.update()

    def _save_settings(self, e: ft.Event | None = None) -> None:
        key = (self.api_key_field.value or "").strip()
        if not key and not env_api_key():
            self.api_key_field.error_text = "Introduce una API key válida."
            self.page.update()
            return

        self.settings.api_key = key
        self.settings.speak = bool(self.speak_switch.value)
        self.settings.autoplay = bool(self.autoplay_switch.value)
        self.settings.stt_model = (self.stt_field.value or "").strip() or "gpt-4o-mini-transcribe"
        self.settings.translation_model = (
            self.translation_field.value or ""
        ).strip() or "gpt-4o-mini"
        self.settings.tts_model = (self.tts_field.value or "").strip() or "gpt-4o-mini-tts"

        try:
            save_settings(self.settings)
        except OSError:
            logger.exception("Could not persist settings")
            self.api_key_field.error_text = "No se pudo guardar el archivo de ajustes."
            self.page.update()
            return

        self._load_engine()
        self._apply_languages(clear=False)
        self.page.pop_dialog()
        self._refresh_controls()
        self._toast("Ajustes guardados.")
