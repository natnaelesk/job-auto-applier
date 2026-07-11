"""Playwright browser tools for the application agent.

Preferred mode: attach to a REAL Chrome/Edge window via CDP
(scripts/start_real_chrome.ps1). Google blocks Playwright's bundled
Firefox/Chromium with "This browser or app may not be secure."

Fallback: launch system Chrome / Edge / Firefox with a persistent profile.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

import config

LogFn = Callable[[str], None]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
TELEGRAM_RE = re.compile(
    r"(https?://)?(t\.me|telegram\.me|web\.telegram\.org)/[^\s)>\]]+",
    re.I,
)
HTTP_RE = re.compile(r"https?://[^\s)>\]]+", re.I)


def _windows_firefox_exe() -> Path | None:
    candidates = [
        Path(r"C:\Program Files\Mozilla Firefox\firefox.exe"),
        Path(r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _default_firefox_profile() -> Path | None:
    """Resolve the default Firefox release profile from profiles.ini."""
    ini = Path(os_appdata_firefox_ini())
    if not ini.exists():
        return None
    text = ini.read_text(encoding="utf-8", errors="ignore")
    # Prefer Install Default=Profiles/... then Profile Path with Name=default-release
    default_rel = None
    for line in text.splitlines():
        if line.startswith("Default=Profiles/"):
            default_rel = line.split("=", 1)[1].strip()
            break
    root = ini.parent
    if default_rel:
        path = root / default_rel.replace("/", "\\")
        if path.is_dir():
            return path
    for line in text.splitlines():
        if line.startswith("Path="):
            rel = line.split("=", 1)[1].strip()
            path = (root / rel) if not Path(rel).is_absolute() else Path(rel)
            if "default-release" in str(path) and path.is_dir():
                return path
    return None


def os_appdata_firefox_ini() -> Path:
    appdata = Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "profiles.ini"
    return appdata


class BrowserSession:
    """Thin wrapper around a headed Playwright page."""

    def __init__(self, log: LogFn | None = None):
        self._log = log or (lambda _m: None)
        self._pw = None
        self._cdp_browser: Browser | None = None
        self._attached = False  # True = do not close the user's real browser
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def start(self) -> None:
        self._pw = sync_playwright().start()
        cdp = (config.PLAYWRIGHT_CDP_URL or "").strip()
        engine = (config.PLAYWRIGHT_BROWSER or "firefox").lower()

        if cdp and engine in {"chrome", "edge", "chromium"}:
            if self._try_cdp(cdp):
                return
            self._log(
                f"CDP not reachable at {cdp} — start real Chrome first:\n"
                f"  powershell -File scripts/start_real_chrome.ps1\n"
                f"Then re-run apply. Falling back to launch…"
            )

        if engine in {"chrome", "edge", "chromium"}:
            self._launch_chromium_family(engine)
        else:
            self._launch_firefox()

    def _try_cdp(self, cdp_url: str) -> bool:
        assert self._pw
        try:
            self._cdp_browser = self._pw.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            self._log(f"CDP connect failed: {e}")
            return False

        self._attached = True
        if self._cdp_browser.contexts:
            self.context = self._cdp_browser.contexts[0]
        else:
            self.context = self._cdp_browser.new_context(accept_downloads=True)

        # Fresh tab so we don't hijack whatever the user was viewing
        try:
            self.page = self.context.new_page()
        except Exception:
            self.page = (
                self.context.pages[0] if self.context.pages else self.context.new_page()
            )
        self.page.set_default_timeout(30_000)
        self._log(f"Attached to REAL browser via CDP ({cdp_url})")
        return True

    def _launch_chromium_family(self, engine: str) -> None:
        assert self._pw
        profile = config.BROWSER_PROFILE_DIR
        profile.mkdir(parents=True, exist_ok=True)

        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(profile),
            "headless": config.PLAYWRIGHT_HEADLESS,
            "viewport": None,
            "accept_downloads": True,
            "ignore_default_args": ["--enable-automation"],
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        }
        if config.PLAYWRIGHT_EXECUTABLE:
            launch_kwargs["executable_path"] = config.PLAYWRIGHT_EXECUTABLE
        elif engine == "chrome":
            launch_kwargs["channel"] = "chrome"
        elif engine == "edge":
            launch_kwargs["channel"] = "msedge"

        self.context = self._pw.chromium.launch_persistent_context(**launch_kwargs)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(30_000)
        self._log(
            f"Browser launched ({engine}/real channel, profile={profile.name})"
        )

    def _launch_firefox(self) -> None:
        assert self._pw
        profile = config.BROWSER_PROFILE_DIR
        # If user pointed at their real Firefox profile, use it (Firefox must be closed).
        exe = config.PLAYWRIGHT_EXECUTABLE or ""
        if not exe:
            found = _windows_firefox_exe()
            exe = str(found) if found else ""

        # Optional: use real Firefox profile when BROWSER_USER_DATA_DIR unset
        # and a dedicated flag — we keep agent profile by default to avoid
        # corrupting the daily Firefox profile. User can set BROWSER_USER_DATA_DIR.
        profile.mkdir(parents=True, exist_ok=True)

        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(profile),
            "headless": config.PLAYWRIGHT_HEADLESS,
            "viewport": None,
            "accept_downloads": True,
            "firefox_user_prefs": {
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False,
            },
        }
        if exe:
            launch_kwargs["executable_path"] = exe
            self._log(f"Using system Firefox: {exe}")
        else:
            self._log("System Firefox not found — using Playwright Firefox build")

        self.context = self._pw.firefox.launch_persistent_context(**launch_kwargs)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(30_000)
        self._log(f"Firefox started (profile={profile.name})")
        self._log(
            "NOTE: Google often still blocks automated Firefox. "
            "For Gmail/Google login prefer scripts/start_real_chrome.ps1 + CDP."
        )

    def stop(self) -> None:
        try:
            if self._attached:
                # Do NOT call browser.close() — that would quit the user's Chrome.
                self._log("Detached from real browser (left open)")
            else:
                if self.context:
                    self.context.close()
                self._log("Browser closed")
            if self._pw:
                self._pw.stop()
        finally:
            self.page = None
            self.context = None
            self._cdp_browser = None
            self._attached = False
            self._pw = None

    def goto(self, url: str, *, wait_ms: int = 1000) -> None:
        assert self.page
        self._log(f"Navigate → {url}")
        self.page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        self.page.wait_for_timeout(wait_ms)

    def reload(self, *, wait_ms: int = 800) -> None:
        assert self.page
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_timeout(wait_ms)

    def detect_human_gate(self) -> str | None:
        """Return a reason if the user must act (login / CAPTCHA), else None."""
        assert self.page
        url = (self.page.url or "").lower()
        title = (self.page.title() or "").lower()
        body = ""
        try:
            body = (self.page.inner_text("body") or "")[:5000].lower()
        except Exception:
            pass

        if any(
            x in url
            for x in (
                "linkedin.com/login",
                "linkedin.com/uas/login",
                "linkedin.com/checkpoint",
                "accounts.google.com",
                "google.com/signin",
            )
        ):
            return "Login required — sign in in the browser, then Continue"

        # Google's automation block page
        if "couldn't sign you in" in body or "browser or app may not be secure" in body:
            return (
                "Google blocked this browser. Use real Chrome: "
                "scripts/start_real_chrome.ps1 then Continue / restart apply"
            )

        patterns = [
            (r"captcha|recaptcha|hcaptcha|cf-turnstile|verify you are human", "CAPTCHA / bot check"),
            (r"unusual traffic|are you a robot", "Bot verification wall"),
            (
                r"(sign in to continue|log in to continue|login required|"
                r"create an account to apply|sign up to apply|"
                r"please log in|please sign in|"
                r"scan the qr code|log in by qr)",
                "Login / account wall",
            ),
        ]
        blob = f"{title}\n{body}"
        for pattern, reason in patterns:
            if re.search(pattern, blob, re.I):
                if "linkedin.com" in url and "easy apply" in body and "login" not in url:
                    continue
                if "linkedin.com/jobs" in url and "checkpoint" not in url:
                    if "sign in" in body and "easy apply" not in body:
                        return reason
                    continue
                return reason
        return None

    def collect_links(self, limit: int = 40) -> list[dict[str, str]]:
        assert self.page
        script = """
        (limit) => {
          const out = [];
          for (const a of Array.from(document.querySelectorAll('a[href]'))) {
            const href = a.href || '';
            const text = (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 120);
            if (!href || href.startsWith('javascript:')) continue;
            out.push({href, text});
            if (out.length >= limit) break;
          }
          return out;
        }
        """
        try:
            return list(self.page.evaluate(script, limit))
        except Exception:
            return []

    def find_telegram_url(self, *blobs: str) -> str | None:
        for blob in blobs:
            if not blob:
                continue
            m = TELEGRAM_RE.search(blob)
            if m:
                url = m.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                return url.rstrip(").,]")
        for link in self.collect_links():
            href = link.get("href") or ""
            if TELEGRAM_RE.search(href) or "afriwork" in href.lower():
                return href
        return None

    def find_email(self, *blobs: str) -> str | None:
        for blob in blobs:
            if not blob:
                continue
            m = EMAIL_RE.search(blob)
            if m:
                return m.group(0)
        for link in self.collect_links():
            href = (link.get("href") or "").lower()
            if href.startswith("mailto:"):
                return href.split(":", 1)[1].split("?")[0]
        return None

    def form_snapshot(self, max_chars: int = 12_000) -> str:
        assert self.page
        script = """
        () => {
          const pick = (el) => {
            const tag = el.tagName.toLowerCase();
            const attrs = ['id','name','type','placeholder','aria-label','role','autocomplete'];
            const a = {};
            for (const k of attrs) {
              const v = el.getAttribute(k);
              if (v) a[k] = v.slice(0, 120);
            }
            let label = '';
            if (el.id) {
              const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
              if (lab) label = (lab.innerText || '').trim().slice(0, 120);
            }
            if (!label) {
              const parentLab = el.closest('label');
              if (parentLab) label = (parentLab.innerText || '').trim().slice(0, 120);
            }
            const opts = [];
            if (tag === 'select') {
              for (const o of Array.from(el.options).slice(0, 20)) {
                opts.push({value: o.value, text: (o.text || '').trim().slice(0, 80)});
              }
            }
            return {tag, attrs: a, label, options: opts, required: !!el.required};
          };
          const nodes = Array.from(document.querySelectorAll(
            'input:not([type=hidden]), textarea, select, button, [role=button], a'
          )).slice(0, 100);
          return {
            url: location.href,
            title: document.title,
            fields: nodes.map(pick),
          };
        }
        """
        data = self.page.evaluate(script)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n…(truncated)"
        return text

    def fill(self, selector: str, value: str) -> None:
        assert self.page
        self._log(f"Fill {selector!r} ← {value[:60]!r}")
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=12_000)
        loc.click()
        loc.fill("")
        loc.fill(str(value))

    def type_keys(self, selector: str, value: str, *, delay: int = 30) -> None:
        assert self.page
        self._log(f"Type {selector!r} ← {value[:60]!r}")
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=12_000)
        loc.click()
        self.page.keyboard.type(str(value), delay=delay)

    def select(self, selector: str, value: str) -> None:
        assert self.page
        self._log(f"Select {selector!r} ← {value!r}")
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=12_000)
        try:
            loc.select_option(value)
        except Exception:
            loc.select_option(label=value)

    def click(self, selector: str) -> None:
        assert self.page
        self._log(f"Click {selector!r}")
        loc = self.page.locator(selector).first
        loc.wait_for(state="visible", timeout=12_000)
        loc.click()

    def upload(self, selector: str, file_path: Path) -> None:
        assert self.page
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Upload file missing: {path}")
        self._log(f"Upload {selector!r} ← {path.name}")
        loc = self.page.locator(selector).first
        loc.set_input_files(str(path))

    def screenshot(self, out_path: Path) -> Path:
        assert self.page
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(out_path), full_page=True)
        self._log(f"Screenshot → {out_path.name}")
        return out_path

    def run_actions(self, actions: list[dict[str, Any]], files: dict[str, Path]) -> None:
        for i, action in enumerate(actions or [], 1):
            op = (action.get("op") or "").lower()
            selector = action.get("selector") or ""
            if not selector and op not in {"wait", "press"}:
                self._log(f"  skip action {i}: missing selector")
                continue
            try:
                if op == "fill":
                    self.fill(selector, str(action.get("value", "")))
                elif op == "type":
                    self.type_keys(selector, str(action.get("value", "")))
                elif op == "select":
                    self.select(selector, str(action.get("value", "")))
                elif op == "click":
                    self.click(selector)
                elif op == "upload":
                    key = str(action.get("file") or "cv")
                    path = files.get(key)
                    if not path:
                        self._log(f"  skip upload: unknown file key {key!r}")
                        continue
                    self.upload(selector, path)
                elif op == "press":
                    key = str(action.get("key") or "Enter")
                    self._log(f"Press {key}")
                    self.page.keyboard.press(key)
                elif op == "wait":
                    ms = int(action.get("ms") or 500)
                    self.page.wait_for_timeout(ms)
                else:
                    self._log(f"  unknown op {op!r}")
            except Exception as e:
                self._log(f"  ! action {i} ({op}) failed: {e}")
                raise
