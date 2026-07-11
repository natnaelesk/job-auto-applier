"""Always-on-top control panel for Phase 5 apply sessions.

Tkinter runs on the main thread; the apply worker runs in a background thread.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import scrolledtext, ttk
from typing import Callable


@dataclass
class JobView:
    job_id: int
    company: str
    title: str
    score: int | None = None
    confidence: str = ""
    notes: str = ""


class ControlPanel:
    """Floating topmost window: logs + Approve / Continue / Skip / Auto / Quit."""

    def __init__(self):
        self._log_q: queue.Queue[str] = queue.Queue()
        self._job_q: queue.Queue[JobView | None] = queue.Queue()
        self._wait_event = threading.Event()
        self._decision: str | None = None
        self._auto = True  # automate submits when confidence allows
        self._paused = False
        self._quit = False
        self._root: tk.Tk | None = None
        self._worker: threading.Thread | None = None
        self._status_label: ttk.Label | None = None
        self._continue_btn: ttk.Button | None = None

    # ----- public API (called from worker thread unless noted) -----

    def run(self, worker: Callable[[], None]) -> None:
        """Start worker in background; block on Tk mainloop (call from main thread)."""
        self._quit = False
        self._worker = threading.Thread(
            target=self._wrap_worker, args=(worker,), daemon=True
        )
        self._worker.start()
        self._run_ui()
        if self._worker.is_alive():
            self._worker.join(timeout=5)

    def _wrap_worker(self, worker: Callable[[], None]) -> None:
        try:
            worker()
        finally:
            self.request_close()

    def request_close(self) -> None:
        self._quit = True
        self._wait_event.set()
        root = self._root
        if root is not None:
            try:
                root.after(0, root.quit)
            except Exception:
                pass

    def log(self, message: str) -> None:
        self._log_q.put(message)

    def set_job(self, job: JobView | None) -> None:
        self._job_q.put(job)

    @property
    def auto_enabled(self) -> bool:
        return self._auto

    @property
    def should_quit(self) -> bool:
        return self._quit

    def wait_while_paused(self) -> None:
        while self._paused and not self._quit:
            threading.Event().wait(0.2)

    def request_decision(self, prompt: str = "Approve submit?") -> str:
        """Block until user clicks Approve / Skip / Manual (or Quit)."""
        return self._wait_for(prompt, default="skip")

    def wait_for_continue(self, prompt: str) -> bool:
        """Block until Continue (or Approve). Returns False if quit/skip."""
        decision = self._wait_for(prompt, default="skip", highlight_continue=True)
        if decision in {"continue", "approve"}:
            return True
        return False

    def _wait_for(
        self,
        prompt: str,
        *,
        default: str = "skip",
        highlight_continue: bool = False,
    ) -> str:
        self._decision = None
        self._wait_event.clear()
        self.log(f"WAITING: {prompt}")
        if self._status_label is not None:
            try:
                self._root.after(
                    0,
                    lambda: self._status_label.config(
                        text=f"Status: WAITING — {prompt[:80]}"
                    ),
                )
            except Exception:
                pass
        if highlight_continue and self._continue_btn is not None:
            try:
                self._root.after(
                    0,
                    lambda: self._status_label.config(
                        text=f"Status: WAITING — click Continue",
                        foreground="#0a5",
                    ),
                )
            except Exception:
                pass
        try:
            import winsound

            winsound.MessageBeep()
        except Exception:
            pass

        while not self._quit:
            if self._wait_event.wait(timeout=0.25):
                break
        if self._status_label is not None:
            try:
                self._root.after(
                    0, lambda: self._status_label.config(foreground="#555")
                )
            except Exception:
                pass
        if self._quit and self._decision is None:
            return "quit"
        return self._decision or default

    # ----- UI thread -----

    def _run_ui(self) -> None:
        root = tk.Tk()
        self._root = root
        root.title("Job Auto-Applier — Control")
        root.geometry("440x560+40+40")
        root.attributes("-topmost", True)
        root.resizable(True, True)

        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        ttk.Label(
            root,
            text="Application Agent",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self._job_label = ttk.Label(
            root,
            text="No job yet",
            wraplength=410,
            justify="left",
            font=("Segoe UI", 9),
        )
        self._job_label.pack(anchor="w", padx=12, pady=(0, 6))

        self._status_label = ttk.Label(root, text="Status: idle", foreground="#555")
        self._status_label.pack(anchor="w", padx=12)

        btn_row = ttk.Frame(root)
        btn_row.pack(fill="x", padx=10, pady=8)

        ttk.Button(
            btn_row, text="Approve & Submit", command=lambda: self._decide("approve")
        ).pack(side="left", padx=2)
        self._continue_btn = ttk.Button(
            btn_row, text="Continue", command=lambda: self._decide("continue")
        )
        self._continue_btn.pack(side="left", padx=2)
        ttk.Button(btn_row, text="Skip", command=lambda: self._decide("skip")).pack(
            side="left", padx=2
        )

        toggle_row = ttk.Frame(root)
        toggle_row.pack(fill="x", padx=10, pady=(0, 6))

        self._auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toggle_row,
            text="Auto (high confidence)",
            variable=self._auto_var,
            command=self._on_auto,
        ).pack(side="left")

        self._pause_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toggle_row,
            text="Pause",
            variable=self._pause_var,
            command=self._on_pause,
        ).pack(side="left", padx=(12, 0))

        ttk.Button(toggle_row, text="Quit", command=self._on_quit).pack(side="right")

        hint = ttk.Label(
            root,
            text="Login / CAPTCHA: finish in the browser, then click Continue.",
            foreground="#666",
            wraplength=410,
        )
        hint.pack(anchor="w", padx=12, pady=(0, 4))

        ttk.Label(root, text="Live log").pack(anchor="w", padx=12)
        self._log_box = scrolledtext.ScrolledText(
            root,
            height=18,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
        )
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._poll()
        root.mainloop()
        self._root = None

    def _decide(self, decision: str) -> None:
        self._decision = decision
        self._wait_event.set()
        if self._status_label is not None:
            self._status_label.config(text=f"Status: decided → {decision}")

    def _on_auto(self) -> None:
        self._auto = bool(self._auto_var.get())
        self.log(f"Auto mode {'ON' if self._auto else 'OFF'}")

    def _on_pause(self) -> None:
        self._paused = bool(self._pause_var.get())
        self.log(f"{'Paused' if self._paused else 'Resumed'}")

    def _on_quit(self) -> None:
        self._quit = True
        self._decision = "quit"
        self._wait_event.set()
        if self._root is not None:
            self._root.quit()

    def _append_log(self, line: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _poll(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                self._append_log(self._log_q.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                job = self._job_q.get_nowait()
                if job is None:
                    self._job_label.config(text="No job yet")
                    self._status_label.config(text="Status: idle")
                else:
                    score = f"{job.score}%" if job.score is not None else "—"
                    conf = job.confidence or "—"
                    self._job_label.config(
                        text=(
                            f"#{job.job_id}  {job.company}\n"
                            f"{job.title}\n"
                            f"Score {score} · Confidence {conf}"
                            + (f"\n{job.notes}" if job.notes else "")
                        )
                    )
                    self._status_label.config(text="Status: working")
        except queue.Empty:
            pass
        if not self._quit:
            self._root.after(150, self._poll)
