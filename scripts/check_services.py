"""Headless-ish check: permission, WAV encoder and input devices.

Run with: uv run flet run -n scripts/check_services.py
It never records audio; it only asks the client what it supports.
"""

from __future__ import annotations

import asyncio
import inspect

import flet as ft

from voice_language.services.audio import RecorderService


async def main(page: ft.Page) -> None:
    recorder = RecorderService(page)
    print(f"DIAG {await recorder.diagnostics()}", flush=True)
    await asyncio.sleep(0.5)
    result = page.window.close()
    if inspect.isawaitable(result):
        await result


if __name__ == "__main__":
    ft.run(main)
