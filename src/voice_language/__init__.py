"""Voice Language: speak one language, hear another."""

from __future__ import annotations

import flet as ft

from .app import configure_logging
from .app import main as build_app

__all__ = ["main"]


def main() -> None:
    configure_logging()
    ft.run(build_app)
