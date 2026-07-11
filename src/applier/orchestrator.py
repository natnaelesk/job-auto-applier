"""Modern CustomTkinter orchestrator — General / Gather / Apply / Updates.

Clean native-looking controls from CustomTkinter. Business logic stays in
applier.agent; this file is UI + threading only.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

import customtkinter as ctk

import db
from applier import agent as apply_agent
from applier import colors as C
from applier.region_capture import capture_region_to

THEME_PATH = Path(__file__).resolve().parents[2] / "assets" / "ctk_theme.json"


class OrchestratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        if THEME_PATH.exists():
            ctk.set_default_color_theme(str(THEME_PATH))
        else:
            ctk.set_default_color_theme("dark-blue")

        self.title("Job Auto-Applier")
        self.geometry("1040x820+40+30")
        self.minsize(860, 640)
        self.resizable(True, True)
        self.configure(fg_color=C.WIN_BG)

        self._log_q: queue.Queue[tuple[str, str]] = queue.Queue()
        self._ui_q: queue.Queue[Callable] = queue.Queue()
        self._session: apply_agent.ApplySession | None = None
        self._busy = False
        self._answer_widgets: list[tuple[ctk.CTkEntry, str]] = []
        self._run_updates_after_apply = True
        self._task_q: queue.Queue[tuple[str, Callable]] = queue.Queue()
        self._worker_started = False
        self._agent_status: dict[str, ctk.CTkLabel] = {}
        self._counter_labels: dict[str, ctk.CTkLabel] = {}
        self._live_progress: ctk.CTkLabel | None = None

        self._start_worker()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._refresh_dashboard)
        self.after(120, self._poll)

    def _primary(self, parent, **kwargs) -> ctk.CTkButton:
        return ctk.CTkButton(parent, **C.PRIMARY_BTN, **kwargs)

    def _secondary(self, parent, **kwargs) -> ctk.CTkButton:
        return ctk.CTkButton(parent, **C.SECONDARY_BTN, **kwargs)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text="Job Auto-Applier",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=C.INK,
        ).pack(side="left")

        self._busy_label = ctk.CTkLabel(
            header,
            text="Idle",
            font=ctk.CTkFont(size=13),
            text_color=C.INK_DIM,
        )
        self._busy_label.pack(side="right", padx=(8, 0))

        self._theme_btn = ctk.CTkSegmentedButton(
            header,
            values=["Dark", "Light"],
            command=self._on_theme,
            width=140,
        )
        self._theme_btn.set("Dark")
        self._theme_btn.pack(side="right", padx=8)

        self._secondary(
            header, text="Refresh", width=90, command=self._refresh_dashboard
        ).pack(side="right", padx=4)

        self._live_progress = ctk.CTkLabel(
            self,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color=C.INK_DIM,
            anchor="w",
        )
        self._live_progress.pack(fill="x", padx=22, pady=(0, 6))

        self._tabs = ctk.CTkTabview(self, corner_radius=12, fg_color=C.SURFACE)
        self._tabs.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        self._tabs.add("General")
        self._tabs.add("Gather")
        self._tabs.add("Apply")
        self._tabs.add("Updates")

        self._build_general(self._tabs.tab("General"))
        self._build_gather(self._tabs.tab("Gather"))
        self._build_apply(self._tabs.tab("Apply"))
        self._build_updates(self._tabs.tab("Updates"))

    def _on_theme(self, value: str) -> None:
        mode = "dark" if value == "Dark" else "light"
        ctk.set_appearance_mode(mode)
        self.configure(fg_color=C.WIN_BG)
        if self._tabs is not None:
            self._tabs.configure(fg_color=C.SURFACE)
        if self._live_progress is not None:
            self._live_progress.configure(text_color=C.INK_DIM)
        self._busy_label.configure(text_color=C.INK_DIM)

    def _build_general(self, parent) -> None:
        parent.configure(fg_color=C.SURFACE)
        ctk.CTkLabel(
            parent,
            text="Dashboard — run agents and watch your pipeline",
            font=ctk.CTkFont(size=13),
            text_color=C.INK_DIM,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 10))

        agents = ctk.CTkFrame(parent, fg_color="transparent")
        agents.pack(fill="x", padx=4, pady=4)
        for i in range(5):
            agents.grid_columnconfigure(i, weight=1)

        specs = [
            ("scan", "1 · Scan", "Telegram channels", self._agent_scan),
            ("extract", "2 · Extract + Match", "Parse & score jobs", self._agent_extract),
            ("cv", "3 · CVs + Notion", "Generate & sync", self._agent_cv),
            ("gmail", "4 · Gmail", "Inbox replies", self._agent_gmail),
            ("all", "5 · Run All", "Full pipeline", self._agent_all),
        ]
        for i, (key, title, subtitle, cmd) in enumerate(specs):
            card = ctk.CTkFrame(agents, corner_radius=12, fg_color=C.SURFACE_2)
            card.grid(row=0, column=i, sticky="nsew", padx=5, pady=4)
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=C.INK,
            ).pack(anchor="w", padx=12, pady=(12, 0))
            ctk.CTkLabel(
                card,
                text=subtitle,
                font=ctk.CTkFont(size=11),
                text_color=C.INK_DIM,
            ).pack(anchor="w", padx=12, pady=(2, 8))
            btn_fn = self._primary if key == "all" else self._secondary
            btn_fn(card, text="Run", height=34, command=cmd).pack(
                fill="x", padx=12, pady=(0, 6)
            )
            st = ctk.CTkLabel(
                card,
                text="Ready",
                font=ctk.CTkFont(size=11),
                text_color=C.MUTED,
            )
            st.pack(anchor="w", padx=12, pady=(0, 12))
            self._agent_status[key] = st

        counts_card = ctk.CTkFrame(parent, corner_radius=12, fg_color=C.SURFACE_2)
        counts_card.pack(fill="x", padx=4, pady=10)
        ctk.CTkLabel(
            counts_card,
            text="Pipeline status",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C.INK,
        ).pack(anchor="w", padx=14, pady=(12, 6))
        self._counter_host = ctk.CTkFrame(counts_card, fg_color="transparent")
        self._counter_host.pack(fill="x", padx=10, pady=(0, 12))
        self._rebuild_counters({})

        boards = ctk.CTkFrame(parent, fg_color="transparent")
        boards.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        boards.grid_columnconfigure(0, weight=3)
        boards.grid_columnconfigure(1, weight=2)
        boards.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(boards, corner_radius=12, fg_color=C.SURFACE_2)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(
            left,
            text="Logs",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C.INK,
        ).pack(anchor="w", padx=12, pady=(10, 4))
        self._general_log = ctk.CTkTextbox(
            left,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        self._general_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._general_log.configure(state="disabled")

        right = ctk.CTkFrame(boards, corner_radius=12, fg_color=C.SURFACE_2)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(
            right,
            text="Email received",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C.INK,
        ).pack(anchor="w", padx=12, pady=(10, 4))
        self._email_board = ctk.CTkTextbox(
            right,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        self._email_board.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._email_board.configure(state="disabled")

    def _rebuild_counters(self, counts: dict[str, int]) -> None:
        for child in self._counter_host.winfo_children():
            child.destroy()
        self._counter_labels.clear()

        keys = ["all", "matched", "review", "applied", "closed", "interview", "offer", "skipped"]
        for i, key in enumerate(keys):
            n = counts.get(key, 0)
            chip = ctk.CTkFrame(self._counter_host, corner_radius=10, fg_color=C.SURFACE)
            chip.grid(row=0, column=i, sticky="nsew", padx=4, pady=2)
            self._counter_host.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(
                chip,
                text=key.upper(),
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=C.STATUS_COLORS.get(key, C.MUTED),
            ).pack(anchor="w", padx=10, pady=(8, 0))
            val = ctk.CTkLabel(
                chip,
                text=str(n),
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=C.INK,
            )
            val.pack(anchor="w", padx=10, pady=(0, 8))
            self._counter_labels[key] = val

    def _set_board(self, widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def _refresh_dashboard(self) -> None:
        counts = db.status_counts()
        self._rebuild_counters(counts)
        self._update_gather_counts()

        emails = db.recent_email_updates(limit=30)
        elines = []
        for r in emails:
            when = (r["last_response_at"] or "")[:19].replace("T", " ")
            company = r["company"] or "?"
            status = r["status"] or "?"
            summary = (r["response_summary"] or "Reply received").strip()
            elines.append(
                f"[{when}]  {company}\n"
                f"  status: {status.upper()}\n"
                f"  {summary}\n"
            )
        self._set_board(
            self._email_board,
            "\n".join(elines)
            if elines
            else "No company emails yet.\nRun Gmail after you apply.",
        )
        if hasattr(self, "_updates_email"):
            self._refresh_updates_emails()

    def _build_gather(self, parent) -> None:
        parent.configure(fg_color=C.SURFACE)
        ctk.CTkLabel(
            parent,
            text="Gather tasks — Scan → Extract/Match → CVs/Notion",
            font=ctk.CTkFont(size=13),
            text_color=C.INK_DIM,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 6))

        self._gather_counts = ctk.CTkLabel(
            parent,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C.INK,
            anchor="w",
        )
        self._gather_counts.pack(fill="x", padx=8, pady=(0, 8))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=4)
        self._primary(row, text="Run Gather 1–4", width=140, command=self._run_gather).pack(
            side="left", padx=4
        )
        self._secondary(row, text="Scan only", width=110, command=self._agent_scan).pack(
            side="left", padx=4
        )
        self._secondary(
            row, text="Extract + Match", width=130, command=self._agent_extract
        ).pack(side="left", padx=4)
        self._secondary(row, text="CVs + Notion", width=120, command=self._agent_cv).pack(
            side="left", padx=4
        )
        self._secondary(row, text="Notion only", width=110, command=self._run_notion).pack(
            side="left", padx=4
        )

        self._gather_log = self._make_log(parent, height=420)
        self._update_gather_counts()

    def _update_gather_counts(self) -> None:
        if not hasattr(self, "_gather_counts"):
            return
        counts = db.status_counts()
        bits = [
            f"All {counts.get('all', 0)}",
            f"Matched {counts.get('matched', 0)}",
            f"Review {counts.get('review', 0)}",
            f"Applied {counts.get('applied', 0)}",
            f"Closed {counts.get('closed', 0)}",
            f"Skipped {counts.get('skipped', 0)}",
        ]
        self._gather_counts.configure(text="  ·  ".join(bits))

    def _build_updates(self, parent) -> None:
        parent.configure(fg_color=C.SURFACE)
        ctk.CTkLabel(
            parent,
            text="Updates — company replies with status",
            font=ctk.CTkFont(size=13),
            text_color=C.INK_DIM,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 8))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=4)
        self._primary(
            row, text="Scan Gmail + Sync", width=160, command=self._run_gmail
        ).pack(side="left", padx=4)
        self._secondary(
            row, text="Refresh boards", width=130, command=self._refresh_dashboard
        ).pack(side="left", padx=4)

        self._updates_email = ctk.CTkTextbox(
            parent,
            height=180,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        self._updates_email.pack(fill="x", padx=8, pady=8)
        self._updates_log = self._make_log(parent, height=280)

    def _build_apply(self, parent) -> None:
        parent.configure(fg_color=C.SURFACE)
        body = ctk.CTkScrollableFrame(parent, fg_color=C.SURFACE)
        body.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(
            body,
            text="Apply — Open Link (Firefox) → Region Shot → ask below → Analyze → Applied/Closed",
            font=ctk.CTkFont(size=12),
            text_color=C.INK_DIM,
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 6))

        self._job_label = ctk.CTkLabel(
            body,
            text="No session yet",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C.INK,
            anchor="w",
            justify="left",
        )
        self._job_label.pack(fill="x", padx=10, pady=(6, 2))

        self._job_details = ctk.CTkTextbox(
            body,
            height=140,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        self._job_details.pack(fill="x", padx=8, pady=(0, 6))
        self._job_details.insert("end", "Job details appear here after Start / Reload.")
        self._job_details.configure(state="disabled")

        nav = ctk.CTkFrame(body, fg_color="transparent")
        nav.pack(fill="x", padx=4, pady=4)
        self._primary(nav, text="Start / Reload", width=120, command=self._apply_start).pack(
            side="left", padx=4
        )
        self._secondary(nav, text="Open Link", width=100, command=self._apply_open).pack(
            side="left", padx=4
        )
        self._secondary(nav, text="Next Job", width=100, command=self._apply_next).pack(
            side="left", padx=4
        )

        shots = ctk.CTkFrame(body, fg_color="transparent")
        shots.pack(fill="x", padx=4, pady=4)
        for text, cmd in [
            ("Page Shot", self._shot_page),
            ("Scroll + Shot", self._shot_scroll),
            ("Region Shot", self._shot_region),
            ("Clear Shots", self._clear_shots),
        ]:
            self._secondary(shots, text=text, width=110, command=cmd).pack(
                side="left", padx=4
            )
        self._shots_label = ctk.CTkLabel(shots, text="Shots: 0", text_color=C.INK_DIM)
        self._shots_label.pack(side="left", padx=8)

        ctk.CTkLabel(
            body,
            text="Message to AI (with screenshots) — e.g. “this page is a different job than the tracker shows”",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C.INK,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        self._ai_chat = ctk.CTkTextbox(
            body,
            height=70,
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        self._ai_chat.pack(fill="x", padx=8, pady=2)

        ai_row = ctk.CTkFrame(body, fg_color="transparent")
        ai_row.pack(fill="x", padx=4, pady=4)
        self._primary(ai_row, text="Analyze Form", width=120, command=self._analyze).pack(
            side="left", padx=4
        )
        self._secondary(
            ai_row, text="Cover Letter", width=110, command=self._cover_letter
        ).pack(side="left", padx=4)
        self._secondary(ai_row, text="Form Fill", width=100, command=self._form_fill).pack(
            side="left", padx=4
        )

        ctk.CTkLabel(
            body,
            text="Suggested answers",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C.INK,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        ans_wrap = ctk.CTkScrollableFrame(body, height=160, fg_color=C.SURFACE_2)
        ans_wrap.pack(fill="x", padx=8, pady=4)
        self._answers_frame = ans_wrap

        ctk.CTkLabel(
            body,
            text="Notes (saved with status)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C.INK,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(6, 2))
        self._notes = ctk.CTkTextbox(
            body, height=70, fg_color=C.LOG_BG, text_color=C.LOG_FG, border_color=C.LINE
        )
        self._notes.pack(fill="x", padx=8, pady=2)

        status = ctk.CTkFrame(body, fg_color="transparent")
        status.pack(fill="x", padx=4, pady=8)
        ctk.CTkButton(
            status, text="Applied", width=100, command=lambda: self._mark("applied"), **C.SUCCESS_BTN
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            status, text="Closed", width=100, command=lambda: self._mark("closed"), **C.DANGER_BTN
        ).pack(side="left", padx=4)
        self._secondary(status, text="Later", width=100, command=lambda: self._mark("later")).pack(
            side="left", padx=4
        )
        self._secondary(
            status, text="Done → Updates", width=130, command=self._finish_to_updates
        ).pack(side="right", padx=4)

        self._apply_log = self._make_log(body, height=120)

    def _make_log(self, parent, height: int = 160) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(
            parent,
            height=height,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C.LOG_BG,
            text_color=C.LOG_FG,
            border_color=C.LINE,
        )
        box.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        box.configure(state="disabled")
        return box

    def log(self, tab: str, msg: str) -> None:
        self._log_q.put((tab, msg))

    def _set_agent(self, key: str, text: str) -> None:
        label = self._agent_status.get(key)
        if label:
            color = C.CRIMSON if text.startswith("Running") else (
                C.SUCCESS if text == "Done" else C.MUTED
            )
            self._ui(lambda l=label, t=text, c=color: l.configure(text=t, text_color=c))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy

        def apply():
            self._busy_label.configure(
                text="Busy…" if busy else "Idle",
                text_color=C.CRIMSON if busy else C.INK_DIM,
            )
            if not busy and self._live_progress is not None:
                self._live_progress.configure(text="Ready")

        self._ui(apply)

    def _start_worker(self) -> None:
        if self._worker_started:
            return
        self._worker_started = True

        def loop():
            while True:
                tab, fn = self._task_q.get()
                self._set_busy(True)
                try:
                    fn()
                except Exception as e:
                    self.log(tab, f"! Error: {e}")
                finally:
                    self._set_busy(False)
                    self._ui(self._refresh_dashboard)
                    self._task_q.task_done()

        threading.Thread(target=loop, daemon=True).start()

    def _bg(self, tab: str, fn: Callable) -> None:
        self._start_worker()
        pending = self._task_q.qsize()
        if pending > 0 or self._busy:
            self.log(
                tab,
                f"Queued (waiting for {pending + (1 if self._busy else 0)} task(s))…",
            )
        self._task_q.put((tab, fn))

    def _poll(self) -> None:
        try:
            while True:
                tab, msg = self._log_q.get_nowait()
                box = {
                    "gather": getattr(self, "_gather_log", None),
                    "apply": getattr(self, "_apply_log", None),
                    "updates": getattr(self, "_updates_log", None),
                    "general": getattr(self, "_general_log", None),
                }.get(tab) or getattr(self, "_apply_log", None)
                if box is None:
                    continue
                box.configure(state="normal")
                box.insert("end", msg + "\n")
                box.see("end")
                box.configure(state="disabled")
                # Live progress strip: one-line current step (counts included)
                if self._live_progress is not None and msg.strip():
                    short = msg.strip().replace("\n", " ")
                    if len(short) > 120:
                        short = short[:117] + "…"
                    self._live_progress.configure(text=short)
        except queue.Empty:
            pass
        try:
            while True:
                cb = self._ui_q.get_nowait()
                cb()
        except queue.Empty:
            pass
        self.after(120, self._poll)

    def _ui(self, fn: Callable) -> None:
        self._ui_q.put(fn)

    def _dual(self, *tabs: str):
        # Always mirror to General Logs so progress is visible everywhere.
        targets = list(dict.fromkeys((*tabs, "general")))

        def _log(msg: str) -> None:
            for tab in targets:
                self.log(tab, msg)

        return _log

    def _agent_scan(self) -> None:
        def work():
            self._set_agent("scan", "Running…")
            apply_agent.run_scan(log=self._dual("gather"))
            self._set_agent("scan", "Done")

        self._bg("gather", work)

    def _agent_extract(self) -> None:
        def work():
            self._set_agent("extract", "Running…")
            apply_agent.run_extract_match(log=self._dual("gather"))
            self._set_agent("extract", "Done")

        self._bg("gather", work)

    def _agent_cv(self) -> None:
        def work():
            self._set_agent("cv", "Running…")
            apply_agent.run_cv_notion(log=self._dual("gather"))
            self._set_agent("cv", "Done")

        self._bg("gather", work)

    def _agent_gmail(self) -> None:
        def work():
            self._set_agent("gmail", "Running…")
            apply_agent.run_gmail_pipeline(log=self._dual("updates"))
            self._set_agent("gmail", "Done")
            self._ui(self._refresh_updates_emails)

        self._bg("updates", work)

    def _agent_all(self) -> None:
        def work():
            for k in ("scan", "extract", "cv", "gmail", "all"):
                self._set_agent(k, "Queued")
            self._set_agent("all", "Running…")
            self._set_agent("scan", "Running…")
            apply_agent.run_scan(log=self._dual("gather"))
            self._set_agent("scan", "Done")
            self._set_agent("extract", "Running…")
            apply_agent.run_extract_match(log=self._dual("gather"))
            self._set_agent("extract", "Done")
            self._set_agent("cv", "Running…")
            apply_agent.run_cv_notion(log=self._dual("gather"))
            self._set_agent("cv", "Done")
            self._set_agent("gmail", "Running…")
            apply_agent.run_gmail_pipeline(log=self._dual("updates"))
            self._set_agent("gmail", "Done")
            self._set_agent("all", "Done")
            self._ui(self._refresh_updates_emails)

        self._bg("general", work)

    def _refresh_updates_emails(self) -> None:
        emails = db.recent_email_updates(limit=40)
        lines = []
        for r in emails:
            when = (r["last_response_at"] or "")[:19].replace("T", " ")
            lines.append(
                f"[{when}] {r['company'] or '?'} · {r['status']}\n"
                f"  {(r['response_summary'] or '').strip()}\n"
            )
        self._set_board(
            self._updates_email,
            "\n".join(lines) if lines else "No replies yet.",
        )

    def _run_gather(self) -> None:
        def work():
            for k in ("scan", "extract", "cv"):
                self._set_agent(k, "Running…")
            apply_agent.run_gather_pipeline(log=self._dual("gather"))
            for k in ("scan", "extract", "cv"):
                self._set_agent(k, "Done")

        self._bg("gather", work)

    def _run_notion(self) -> None:
        def work():
            import notion_tracker

            log = self._dual("gather")
            log("[Notion] Starting…")
            c, u = notion_tracker.sync_jobs(log=log)
            log(f"[Notion] Summary: {c} created, {u} updated")

        self._bg("gather", work)

    def _run_gmail(self) -> None:
        self._agent_gmail()

    def _ensure_session(self) -> apply_agent.ApplySession:
        if self._session is None:
            self._session = apply_agent.ApplySession(log=lambda m: self.log("apply", m))
        return self._session

    def _refresh_job_label(self) -> None:
        s = self._session
        if not s or not s.job:
            self._job_label.configure(text="No job loaded")
            self._set_board(self._job_details, "No job loaded.")
            return
        j = s.job
        import re

        import config
        from cover_letter import COVER_DIR, _safe_filename

        cv_name = Path(j["cv_path"]).name if j["cv_path"] else "(no CV yet)"
        cv_path = j["cv_path"] or ""
        skills = j["skills"] or "[]"
        if isinstance(skills, str) and len(skills) > 200:
            skills = skills[:200] + "…"
        reasons = j["match_reasons"] or ""
        if isinstance(reasons, str) and len(reasons) > 240:
            reasons = reasons[:240] + "…"
        desc = (j["description"] or "").strip() or "(no description)"
        if len(desc) > 900:
            desc = desc[:900] + "…"

        notion_id = j["notion_page_id"] or ""
        notion_line = "not synced"
        if notion_id:
            clean = notion_id.replace("-", "")
            notion_line = f"{notion_id}\n  https://www.notion.so/{clean}"

        cover_dir = COVER_DIR
        cover_name = (
            f"CoverLetter_{_safe_filename(j['company'] or '')}_"
            f"{_safe_filename(j['title'] or '')}.pdf"
        )
        cover_path = cover_dir / cover_name
        if cover_path.exists():
            cover_line = cover_path.name
        else:
            token = re.sub(r"[^\w]+", "_", (j["company"] or "")[:30]).strip("_")
            hits = sorted(cover_dir.glob(f"CoverLetter_{token}*")) if cover_dir.exists() and token else []
            cover_line = hits[-1].name if hits else "(none yet — click Cover Letter)"

        self._job_label.configure(
            text=(
                f"#{j['id']}  [{j['status']}]  score={j['match_score']}\n"
                f"{j['company']} — {j['title']}"
            )
        )
        details = (
            f"CV: {cv_name}\n"
            f"CV path: {cv_path}\n"
            f"Cover letter: {cover_line}\n"
            f"Cover folder: {cover_dir}\n"
            f"Location: {j['location'] or '—'}\n"
            f"Salary: {j['salary'] or '—'}\n"
            f"Experience: {j['experience'] or '—'}\n"
            f"Apply method: {j['apply_method'] or '—'}  ·  target: {j['apply_target'] or '—'}\n"
            f"Link: {j['link'] or '—'}\n"
            f"Notion: {notion_line}\n"
            f"Skills: {skills}\n"
            f"Match reasons: {reasons or '—'}\n"
            f"Notes: {j['notes'] or '—'}\n"
            f"\n--- About the job ---\n{desc}"
        )
        self._set_board(self._job_details, details)
        self._shots_label.configure(text=f"Shots: {len(s.shots)}")

    def _render_answers(self, fields: list[dict]) -> None:
        for child in self._answers_frame.winfo_children():
            child.destroy()
        self._answer_widgets.clear()
        for i, f in enumerate(fields):
            label = f.get("label") or f"Field {i + 1}"
            answer = f.get("answer") or ""
            row = ctk.CTkFrame(self._answers_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=label, width=180, anchor="w", text_color=C.INK_DIM
            ).pack(side="left")
            ent = ctk.CTkEntry(
                row, fg_color=C.LOG_BG, border_color=C.LINE, text_color=C.INK
            )
            ent.insert(0, answer)
            ent.pack(side="left", fill="x", expand=True, padx=6)

            def copy_one(e=ent):
                self.clipboard_clear()
                self.clipboard_append(e.get())
                self.log("apply", f"Copied: {e.get()[:60]}")

            self._secondary(row, text="Copy", width=60, command=copy_one).pack(side="right")
            self._answer_widgets.append((ent, label))

    def _apply_start(self) -> None:
        def work():
            s = self._ensure_session()
            resume_id = int(s.job["id"]) if s.job else None
            s.start(resume_id=resume_id)
            self._ui(self._refresh_job_label)
            # Do not auto-open a different job — resume current; user clicks Open Link

        self._bg("apply", work)

    def _apply_open(self) -> None:
        def work():
            s = self._ensure_session()
            if not s.jobs:
                s.start()
            s.open_current()
            self._ui(self._refresh_job_label)
            self._ui(lambda: self._render_answers([]))

        self._bg("apply", work)

    def _apply_next(self) -> None:
        def work():
            s = self._ensure_session()
            if not s.next_job():
                self.log("apply", "Queue finished — use Done → Updates when ready.")
            self._ui(self._refresh_job_label)
            self._ui(lambda: self._render_answers([]))
            self._ui(lambda: self._notes.delete("1.0", "end"))

        self._bg("apply", work)

    def _shot_page(self) -> None:
        def work():
            s = self._ensure_session()
            s.screenshot_page()
            self._ui(self._refresh_job_label)

        self._bg("apply", work)

    def _shot_scroll(self) -> None:
        def work():
            s = self._ensure_session()
            s.screenshot_scroll()
            self._ui(self._refresh_job_label)

        self._bg("apply", work)

    def _shot_region(self) -> None:
        s = self._ensure_session()
        if not s.job:
            self.log("apply", "Start a job first")
            return
        path = s._next_shot_path("region")
        self.log("apply", "Drag a rectangle on screen, then Enter…")
        saved = capture_region_to(path)
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass
        if saved:
            s.shots.append(saved)
            self.log("apply", f"Region saved: {saved.name}")
            self._refresh_job_label()
        else:
            self.log("apply", "Region capture cancelled")

    def _clear_shots(self) -> None:
        s = self._session
        if s:
            s.shots.clear()
            self._refresh_job_label()
            self.log("apply", "Screenshots cleared")

    def _analyze(self) -> None:
        def work():
            s = self._ensure_session()
            note_holder: dict[str, str] = {"text": ""}
            done = threading.Event()

            def read_note():
                note_holder["text"] = self._ai_chat.get("1.0", "end").strip()
                done.set()

            self._ui(read_note)
            done.wait(timeout=5)
            fields = s.analyze_form(user_note=note_holder["text"])
            self._ui(lambda: self._render_answers(fields))
            self._ui(self._refresh_job_label)

        self._bg("apply", work)

    def _cover_letter(self) -> None:
        def work():
            s = self._ensure_session()
            note_holder: dict[str, str] = {"text": ""}
            done = threading.Event()

            def read_note():
                note_holder["text"] = self._ai_chat.get("1.0", "end").strip()
                done.set()

            self._ui(read_note)
            done.wait(timeout=5)
            path = s.generate_cover_letter(user_note=note_holder["text"])
            if path:
                self._ui(self._refresh_job_label)

        self._bg("apply", work)

    def _form_fill(self) -> None:
        def work():
            s = self._ensure_session()
            if self._answer_widgets:
                s.answers = [
                    {
                        "label": lab,
                        "answer": ent.get(),
                        "field_type": "text",
                        "confidence": "high",
                    }
                    for ent, lab in self._answer_widgets
                ]
            s.form_fill()

        self._bg("apply", work)

    def _mark(self, status: str) -> None:
        def work():
            s = self._ensure_session()
            notes = ""
            done = threading.Event()

            def ui_read():
                nonlocal notes
                notes = self._notes.get("1.0", "end").strip()
                if self._answer_widgets:
                    s.answers = [
                        {
                            "label": lab,
                            "answer": ent.get(),
                            "field_type": "text",
                            "confidence": "high",
                        }
                        for ent, lab in self._answer_widgets
                    ]
                done.set()

            self._ui(ui_read)
            done.wait(timeout=5)
            s.set_status(status, notes=notes)
            self.log("apply", "Moving to next job…")
            advanced = s.next_job()
            self._ui(lambda: self._notes.delete("1.0", "end"))
            self._ui(lambda: self._render_answers([]))
            self._ui(self._refresh_job_label)
            if not advanced:
                self.log(
                    "apply",
                    "Queue finished — click Done → Updates, or Start / Reload.",
                )

        self._bg("apply", work)

    def _finish_to_updates(self) -> None:
        self.log("apply", "Apply session paused — switching to Updates…")
        self._tabs.set("Updates")
        if self._run_updates_after_apply:
            self._run_gmail()

    def _on_close(self) -> None:
        if self._session:
            try:
                self._session.stop()
            except Exception:
                pass
        self.destroy()


def launch() -> None:
    app = OrchestratorApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
