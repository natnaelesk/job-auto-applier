"""Multi-monitor translucent overlay to pick a screen region (drag rectangle)."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path


def _virtual_screen() -> tuple[int, int, int, int]:
    """Return (x, y, width, height) covering every attached display."""
    if sys.platform == "win32":
        import ctypes

        user32 = ctypes.windll.user32
        # SM_XVIRTUALSCREEN / Y / CX / CY
        x = int(user32.GetSystemMetrics(76))
        y = int(user32.GetSystemMetrics(77))
        w = int(user32.GetSystemMetrics(78))
        h = int(user32.GetSystemMetrics(79))
        if w > 0 and h > 0:
            return x, y, w, h
    # Fallback: primary monitor only
    root = tk.Tk()
    root.withdraw()
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()
    return 0, 0, w, h


def capture_region_to(path: Path) -> Path | None:
    """Show a dim overlay across ALL monitors; user drags a rectangle.

    Saves PNG to path. Returns None if cancelled.
    """
    try:
        from PIL import ImageGrab
    except ImportError as e:
        raise SystemExit("Pillow required for region screenshots: pip install Pillow") from e

    vx, vy, vw, vh = _virtual_screen()
    result: dict = {"box": None}
    existing = tk._default_root
    root = tk.Toplevel(existing) if existing else tk.Tk()
    root.title("Select area — drag across any display")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.28)
    except Exception:
        pass
    root.configure(bg="black")
    # Cover the full virtual desktop (multi-monitor), including negative offsets
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.update_idletasks()

    canvas = tk.Canvas(root, cursor="cross", bg="gray20", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    state: dict = {"x0": 0, "y0": 0, "rect": None}

    def on_press(e):
        state["x0"], state["y0"] = e.x, e.y
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#00ff88", width=2
        )

    def on_drag(e):
        if state["rect"]:
            canvas.coords(state["rect"], state["x0"], state["y0"], e.x, e.y)

    def on_release(e):
        x0, y0 = state["x0"], state["y0"]
        x1, y1 = e.x, e.y
        left, top = min(x0, x1), min(y0, y1)
        right, bottom = max(x0, x1), max(y0, y1)
        if right - left > 5 and bottom - top > 5:
            # Canvas coords → absolute virtual-screen coords
            result["box"] = (left + vx, top + vy, right + vx, bottom + vy)

    def confirm(_e=None):
        root.destroy()

    def cancel(_e=None):
        result["box"] = None
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Return>", confirm)
    root.bind("<Escape>", cancel)
    canvas.bind("<Double-Button-1>", confirm)

    hint = tk.Label(
        root,
        text="All displays · Drag to select · Enter / double-click = save · Esc = cancel",
        fg="white",
        bg="black",
        font=("Segoe UI", 12),
    )
    hint.place(relx=0.5, y=24, anchor="n")

    if existing:
        root.grab_set()
        root.focus_force()
        root.wait_window()
    else:
        root.mainloop()

    box = result["box"]
    if not box:
        return None

    # all_screens=True is required on Windows multi-monitor for correct coords
    img = ImageGrab.grab(bbox=box, all_screens=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
