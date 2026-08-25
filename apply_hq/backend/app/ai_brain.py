"""AI brain interface — Cursor SDK when available, stub otherwise.

Never fake success. Callers must handle AIUnavailableError.

Includes the Windows cursor-sdk bridge patch (WinError 10038): cursor-sdk
uses select() on a pipe for discovery, which only works on sockets on Windows.
Same fix as src/ai.py.
"""
from __future__ import annotations

import json
import queue
import re
import sys
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AIUnavailableError(RuntimeError):
    """Raised when CURSOR_API_KEY / profile / SDK is missing or broken."""


def _patch_bridge_for_windows() -> None:
    """cursor-sdk uses select() on a pipe for bridge discovery — WinError 10038
    on Windows. Replace with a threaded blocking-read discovery reader."""
    if sys.platform != "win32":
        return
    try:
        from cursor_sdk import _bridge
        from cursor_sdk.errors import CursorSDKError
    except Exception:
        return

    def _read_discovery_win(process, timeout):
        if process.stderr is None:
            raise CursorSDKError("Bridge process stderr is unavailable")

        lines_q: queue.Queue = queue.Queue()

        def reader():
            try:
                for line in process.stderr:
                    lines_q.put(line)
            except Exception:
                pass
            lines_q.put(None)

        threading.Thread(target=reader, daemon=True).start()

        deadline = time.monotonic() + timeout
        seen: list[str] = []
        while time.monotonic() < deadline:
            try:
                line = lines_q.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                code = process.poll()
                raise CursorSDKError(
                    f"Bridge exited before discovery with status {code}: "
                    + "".join(seen)
                )
            seen.append(line)
            discovery = _bridge.parse_discovery_line(line)
            if discovery is not None:
                return discovery
        raise CursorSDKError("Timed out waiting for bridge discovery")

    _bridge._read_discovery = _read_discovery_win


_patch_bridge_for_windows()


class AIBrain(ABC):
    @abstractmethod
    def ask_json(self, prompt: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def available(self) -> tuple[bool, str]:
        ...


class StubAIBrain(AIBrain):
    """Explicit stub — generation endpoints return 503, never fake PDFs."""

    def __init__(self, reason: str = "AI unavailable"):
        self.reason = reason

    def available(self) -> tuple[bool, str]:
        return False, self.reason

    def ask_json(self, prompt: str) -> dict[str, Any]:
        raise AIUnavailableError(self.reason)


class CursorAIBrain(AIBrain):
    """Thin wrapper around repo Cursor SDK (optional dependency)."""

    def __init__(self, api_key: str, model: str, cwd: Path, prompts_dir: Path):
        self.api_key = api_key
        self.model = model
        self.cwd = cwd
        self.prompts_dir = prompts_dir
        self._err: str | None = None
        try:
            _patch_bridge_for_windows()
            from cursor_sdk import Agent, AgentOptions, LocalAgentOptions  # noqa: F401
        except Exception as e:
            self._err = f"cursor-sdk not importable: {e}"

    def available(self) -> tuple[bool, str]:
        if self._err:
            return False, self._err
        if not self.api_key:
            return False, "CURSOR_API_KEY missing"
        return True, "ok"

    def ask(self, prompt: str) -> str:
        ok, reason = self.available()
        if not ok:
            raise AIUnavailableError(reason)
        # Re-apply patch in case SDK was imported before our module on Windows
        _patch_bridge_for_windows()
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=self.api_key,
                model=self.model,
                local=LocalAgentOptions(cwd=str(self.cwd)),
            ),
        )
        if result.status == "error":
            raise RuntimeError(f"AI run failed (run id: {result.id})")
        return result.result or ""

    def ask_json(self, prompt: str) -> dict[str, Any]:
        text = self.ask(prompt).strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            raise RuntimeError("AI returned non-object JSON")
        return data

    def load_prompt(self, name: str, **kwargs: Any) -> str:
        path = self.prompts_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt missing: {path}")
        template = path.read_text(encoding="utf-8")
        for key, value in kwargs.items():
            template = template.replace("{" + key + "}", str(value))
        return template


def get_brain() -> AIBrain:
    from . import config

    ok, reason = config.ai_ready()
    if not ok:
        return StubAIBrain(reason)
    try:
        brain = CursorAIBrain(
            api_key=config.CURSOR_API_KEY,
            model=config.CURSOR_MODEL,
            cwd=config.REPO_ROOT,
            prompts_dir=config.PROMPTS_DIR,
        )
        avail, why = brain.available()
        if not avail:
            return StubAIBrain(why)
        return brain
    except Exception as e:
        return StubAIBrain(f"AI init failed: {e}")
