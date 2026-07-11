"""App color tokens for CustomTkinter orchestrator.

CTk tuple order is always (light_mode, dark_mode).
Palette: #0a100d, #b9baa3, #d6d5c9, #a22c29, #902923
"""

BG_DARK = "#0a100d"
SAGE = "#b9baa3"
CREAM = "#d6d5c9"
CRIMSON = "#a22c29"
CRIMSON_DEEP = "#902923"

PANEL_DARK = "#121a16"
PANEL2_DARK = "#18231d"
BORDER_DARK = "#2a332e"
MUTED = "#8a8d7a"
SUCCESS = "#4a7c59"
WARN = "#c4a35a"

# Convenience singles (dark-leaning) for status text that stays readable
BG = BG_DARK
PANEL = PANEL_DARK
PANEL_2 = PANEL2_DARK
BORDER = BORDER_DARK
TEXT = CREAM
TEXT_DIM = SAGE
ACCENT = CRIMSON
ACCENT_HOVER = CRIMSON_DEEP
DANGER = CRIMSON

# CTk adaptive pairs: (light, dark)
WIN_BG = (CREAM, BG_DARK)
SURFACE = ("#ebeae3", PANEL_DARK)
SURFACE_2 = (SAGE, PANEL2_DARK)
INK = (BG_DARK, CREAM)
INK_DIM = ("#403d39", SAGE)
LINE = (SAGE, BORDER_DARK)
LOG_BG = ("#f3f2ec", BG_DARK)
LOG_FG = (BG_DARK, SAGE)

STATUS_COLORS = {
    "all": SAGE,
    "matched": CRIMSON,
    "review": WARN,
    "applied": SUCCESS,
    "applying": SUCCESS,
    "interview": SUCCESS,
    "offer": SUCCESS,
    "later": MUTED,
    "closed": CRIMSON_DEEP,
    "rejected": CRIMSON_DEEP,
    "skipped": MUTED,
    "found": MUTED,
    "manual": WARN,
    "failed": CRIMSON,
}

PRIMARY_BTN = {
    "fg_color": CRIMSON,
    "hover_color": CRIMSON_DEEP,
    "text_color": CREAM,
}

SECONDARY_BTN = {
    "fg_color": SURFACE_2,
    "hover_color": (CRIMSON, BORDER_DARK),
    "text_color": INK,
    "border_width": 1,
    "border_color": LINE,
}

SUCCESS_BTN = {
    "fg_color": SUCCESS,
    "hover_color": "#3d6849",
    "text_color": CREAM,
}

DANGER_BTN = {
    "fg_color": CRIMSON_DEEP,
    "hover_color": "#6f1f1c",
    "text_color": CREAM,
}
