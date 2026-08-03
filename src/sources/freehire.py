"""freehire.dev public REST API — port of ai-job-search freehire-search skill."""
from __future__ import annotations

import html
import re
import time
from typing import Any
from urllib.parse import urlencode

import requests

import config
from sources.base import Emit, JobSource

UA = "job-auto-applier/1.0 (+https://github.com/natnaelesk/job-auto-applier)"


def _clean_html(raw: str | None) -> str | None:
    if not raw:
        return None
    with_breaks = re.sub(r"<\s*br\s*/?>", "\n", raw, flags=re.I)
    with_breaks = re.sub(r"</(p|li|ul|ol|div|h\d)>", "\n", with_breaks, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", with_breaks))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text or None


def _format_salary(enrichment: dict | None) -> str | None:
    if not enrichment:
        return None
    lo = enrichment.get("salary_min")
    hi = enrichment.get("salary_max")
    if lo is None and hi is None:
        return None
    cur = enrichment.get("salary_currency") or ""
    prefix = f"{cur} " if cur else ""
    if lo is not None and hi is not None:
        return f"{prefix}{lo}-{hi}"
    return f"{prefix}{lo if lo is not None else hi}"


class FreehireSource(JobSource):
    name = "freehire"

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.FREEHIRE_API_URL).rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": UA, "Accept": "application/json"})

    def _get(self, path: str) -> dict | None:
        url = f"{self.base_url}{path}"
        delay = 0.5
        for attempt in range(7):
            try:
                resp = self._session.get(url, timeout=30)
            except requests.RequestException as e:
                raise RuntimeError(f"could not reach freehire API at {self.base_url}: {e}") from e
            if resp.status_code == 404:
                return None
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == 6:
                    raise RuntimeError(
                        f"freehire API failed: {resp.status_code} {resp.reason}"
                    )
                time.sleep(delay + (0.1 * attempt))
                delay = min(delay * 2, 8)
                continue
            if not resp.ok:
                try:
                    body = resp.json()
                    msg = body.get("error") or resp.reason
                except Exception:
                    msg = resp.reason
                raise RuntimeError(f"freehire API failed: {msg}")
            return resp.json()
        raise RuntimeError("freehire API failed after retries")

    def detail(self, slug: str) -> dict | None:
        env = self._get(f"/api/v1/jobs/{requests.utils.quote(slug, safe='')}")
        if not env or not env.get("data"):
            return None
        return self._to_job(env["data"], fetch_full=False)

    def search(
        self,
        queries: list[str],
        *,
        location: str = "Remote",
        days: int = 14,
        limit: int = 20,
        log: Emit | None = None,
    ) -> list[dict]:
        emit = log or (lambda _m: None)
        seen: set[str] = set()
        out: list[dict] = []
        work_mode = "remote" if "remote" in (location or "").lower() else None

        for q in queries:
            params: dict[str, Any] = {
                "q": q,
                "limit": limit,
                "offset": 0,
                "semantic_ratio": "0",
            }
            if days > 0:
                params["posted_within_days"] = days
            if work_mode:
                params["work_mode"] = work_mode
            # Prefer junior / mid for ~1yr profile
            params["seniority"] = ["junior", "mid", "entry"]

            path = f"/api/v1/jobs/search?{urlencode(params, doseq=True)}"
            emit(f"[freehire] search q={q!r}…")
            try:
                env = self._get(path)
            except Exception as e:
                emit(f"[freehire] ! {e}")
                continue
            jobs = (env or {}).get("data") or []
            emit(f"[freehire] {len(jobs)} hit(s) for {q!r}")
            for raw in jobs:
                slug = raw.get("public_slug") or ""
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                # Enrich with full description when search payload is thin
                job = self._to_job(raw, fetch_full=True)
                if job:
                    out.append(job)
            time.sleep(0.4)
        return out

    def _to_job(self, raw: dict, *, fetch_full: bool) -> dict | None:
        slug = raw.get("public_slug") or ""
        title = (raw.get("title") or "").strip()
        if not title:
            return None
        link = (raw.get("url") or "").strip()
        if not link and slug:
            link = f"{self.base_url}/jobs/{slug}"

        description = _clean_html(raw.get("description"))
        enrichment = raw.get("enrichment") or {}
        if fetch_full and (not description or len(description) < 80) and slug:
            try:
                env = self._get(f"/api/v1/jobs/{requests.utils.quote(slug, safe='')}")
                if env and env.get("data"):
                    raw = env["data"]
                    description = _clean_html(raw.get("description")) or description
                    enrichment = raw.get("enrichment") or enrichment
            except Exception:
                pass

        skills = list(raw.get("skills") or [])
        seniority = enrichment.get("seniority")
        experience = seniority
        salary = _format_salary(enrichment)
        location = raw.get("location") or ""
        work_mode = raw.get("work_mode")
        if work_mode and work_mode.lower() == "remote" and "remote" not in location.lower():
            location = f"{location}, Remote".strip(", ") if location else "Remote"

        return {
            "company": raw.get("company") or "Unknown",
            "title": title,
            "location": location or "Remote",
            "salary": salary,
            "experience": experience,
            "skills": skills,
            "link": link,
            "apply_method": "url",
            "apply_target": link,
            "description": description or title,
            "market": "foreign",
            "source": "freehire",
        }
