"""Thin wrapper around the Cursor SDK - the AI brain for judgment steps.

Every AI call in the project goes through ask(): give it a prompt, get text back.
Keeping this in one file means swapping models or adding logging happens in
exactly one place.
"""
import json
import queue
import re
import sys
import threading
import time
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
from cursor_sdk.types import SDKImage, UserMessage

import config


def _patch_bridge_for_windows() -> None:
    """cursor-sdk 0.1.9 uses select() on a pipe to read the bridge's startup
    handshake - that only works on sockets on Windows (WinError 10038).
    Replace the discovery reader with a threaded, blocking-read version."""
    if sys.platform != "win32":
        return

    from cursor_sdk import _bridge
    from cursor_sdk.errors import CursorSDKError

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
            lines_q.put(None)  # EOF sentinel

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


def ask(prompt: str | UserMessage) -> str:
    """One-shot AI call. Raises SystemExit with a clear message if no key set."""
    api_key = config.require("CURSOR_API_KEY", config.CURSOR_API_KEY)
    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=config.CURSOR_MODEL,
            local=LocalAgentOptions(cwd=str(config.PROJECT_ROOT)),
        ),
    )
    if result.status == "error":
        raise RuntimeError(f"AI run failed (run id: {result.id})")
    return result.result or ""


def ask_with_images(prompt: str, image_paths: list[Path | str]) -> str:
    """AI call with screenshot / image attachments."""
    images = []
    for p in image_paths:
        path = Path(p)
        if path.exists():
            images.append(SDKImage.from_file(path))
    if not images:
        return ask(prompt)
    return ask(UserMessage(text=prompt, images=images))


def ask_json(prompt: str | UserMessage):
    """AI call that must return JSON. Strips markdown fences if the model adds them."""
    text = ask(prompt).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def ask_json_with_images(prompt: str, image_paths: list[Path | str]):
    text = ask_with_images(prompt, image_paths).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def load_prompt(name: str, **kwargs) -> str:
    """Load a prompt template from prompts/ and fill {placeholders}."""
    template = (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    for key, value in kwargs.items():
        template = template.replace("{" + key + "}", str(value))
    return template
