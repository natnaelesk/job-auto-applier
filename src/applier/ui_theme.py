"""Neo-brutal / ink design tokens for the Tk orchestrator.

Palette (user): cream #fffcf2, stone #ccc5b9, ink #403d39, deep #252422, flame #eb5e28
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    panel: str
    panel_alt: str
    ink: str
    muted: str
    accent: str
    accent_text: str
    border: str
    success: str
    warn: str
    danger: str
    shadow: str
    chip_bg: str
    log_bg: str
    log_fg: str


LIGHT = Theme(
    name="light",
    bg="#fffcf2",
    panel="#ffffff",
    panel_alt="#ccc5b9",
    ink="#252422",
    muted="#403d39",
    accent="#eb5e28",
    accent_text="#fffcf2",
    border="#252422",
    success="#2f6b3a",
    warn="#a35a00",
    danger="#9b1c1c",
    shadow="#252422",
    chip_bg="#fffcf2",
    log_bg="#252422",
    log_fg="#fffcf2",
)

DARK = Theme(
    name="dark",
    bg="#252422",
    panel="#403d39",
    panel_alt="#2f2c29",
    ink="#fffcf2",
    muted="#ccc5b9",
    accent="#eb5e28",
    accent_text="#fffcf2",
    border="#fffcf2",
    success="#7dcea0",
    warn="#f0c674",
    danger="#ff8a7a",
    shadow="#000000",
    chip_bg="#2f2c29",
    log_bg="#1a1918",
    log_fg="#fffcf2",
)

FONT = ("Space Grotesk", "Segoe UI", "Arial")
FONT_MONO = ("Cascadia Mono", "Consolas", "Courier New")

STATUS_ORDER = [
    "matched",
    "review",
    "applied",
    "applying",
    "later",
    "closed",
    "interview",
    "offer",
    "rejected",
    "skipped",
    "found",
    "manual",
    "failed",
]


def status_color(theme: Theme, status: str) -> str:
    return {
        "matched": theme.accent,
        "review": theme.warn,
        "applied": theme.success,
        "applying": theme.success,
        "interview": theme.success,
        "offer": theme.success,
        "later": theme.muted,
        "closed": theme.danger,
        "rejected": theme.danger,
        "skipped": theme.muted,
        "found": theme.muted,
        "manual": theme.warn,
        "failed": theme.danger,
    }.get(status, theme.muted)
