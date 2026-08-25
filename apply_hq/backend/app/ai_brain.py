"""AI brain interface — Cursor SDK when available, stub otherwise.

Never fake success. Callers must handle AIUnavailableError.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AIUnavailableError(RuntimeError):
    """Raised when CURSOR_API_KEY / profile / SDK is missing or broken."""


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
