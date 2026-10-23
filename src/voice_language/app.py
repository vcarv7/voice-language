"""Flet application entry point."""

from __future__ import annotations

import logging

import flet as ft

from .services.settings import load_settings
from .ui.home import HomeView


def main(page: ft.Page) -> None:
    page.title = "Voice Language"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 24
    page.window.width = 1080
    page.window.height = 780
    page.window.min_width = 760
    page.window.min_height = 640

    settings = load_settings()
    HomeView(page, settings).mount()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
