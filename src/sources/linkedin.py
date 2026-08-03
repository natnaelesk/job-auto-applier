"""LinkedIn public jobs-guest endpoints — port of ai-job-search linkedin-search.

Personal / low-volume use only. Automated access violates LinkedIn ToS if abused.
"""
from __future__ import annotations

import html as html_mod
import random
import re
import time
from typing import Any
from urllib.parse import urlencode

import requests

import config
from sources.base import Emit, JobSource

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _decode(text: str) -> str:
    return html_mod.unescape(text)


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", _decode(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _jobage_to_tpr(days: int) -> str | None:
    if not days or days <= 0 or days >= 9999:
        return None
    return f"r{days * 86400}"


def _work_type_flag(mode: str | None) -> str | None:
    m = (mode or "").lower()
    if m == "remote":
        return "2"
    if m == "hybrid":
        return "3"
    if m in {"onsite", "on-site"}:
        return "1"
    return None


def parse_job_cards(html: str) -> list[dict]:
    results: list[dict] = []
    chunks = html.split('data-entity-urn="urn:li:jobPosting:')[1:]
    for chunk in chunks:
        id_m = re.match(r"^(\d+)", chunk)
        if not id_m:
            continue
        job_id = id_m.group(1)

        link_m = re.search(
            r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', chunk, re.I
        )
        url = _decode(link_m.group(1)).split("?")[0] if link_m else ""

        title = None
        h3 = re.search(
            r'class="base-search-card__title"[^>]*>([\s\S]*?)</h3>', chunk, re.I
        )
        if h3:
            title = _clean(h3.group(1))
        if not title:
            sr = re.search(r'class="sr-only"[^>]*>([\s\S]*?)</span>', chunk, re.I)
            if sr:
                title = _clean(sr.group(1))
        if not title:
            continue

        company = None
        company_url = None
        sub = re.search(
            r'class="base-search-card__subtitle"[^>]*>([\s\S]*?)</h4>', chunk, re.I
        )
        if sub:
            a = re.search(r'href="([^"]+)"', sub.group(1), re.I)
            if a:
                company_url = _decode(a.group(1)).split("?")[0]
            company = _clean(sub.group(1)) or None

        loc = re.search(
            r'class="job-search-card__location"[^>]*>([\s\S]*?)</span>', chunk, re.I
        )
        location = _clean(loc.group(1)) if loc else None
        dt = re.search(
            r'class="job-search-card__listdate[^"]*"[^>]*datetime="([^"]+)"',
            chunk,
            re.I,
        )
        date = dt.group(1) if dt else None

        results.append(
            {
                "id": job_id,
                "title": title,
                "company": company,
                "company_url": company_url,
                "location": location,
                "date": date,
                "url": url or f"https://www.linkedin.com/jobs/view/{job_id}",
            }
        )
    return results


def parse_job_detail(html: str, job_id: str) -> dict:
    title_m = re.search(
        r'class="(?:top-card-layout__title|topcard__title)[^"]*"[^>]*>([\s\S]*?)</h[12]>',
        html,
        re.I,
    )
    org_m = re.search(
        r'class="topcard__org-name-link[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>',
        html,
        re.I,
    )
    company = _clean(org_m.group(2)) if org_m else None
    company_url = _decode(org_m.group(1)).split("?")[0] if org_m else None

    loc_m = re.search(
        r'class="topcard__flavor topcard__flavor--bullet"[^>]*>([\s\S]*?)</span>',
        html,
        re.I,
    )
    location = _clean(loc_m.group(1)) if loc_m else None

    description = None
    desc = re.search(
        r'class="(?:show-more-less-html__markup|description__text[^"]*)"[^>]*>([\s\S]*?)</div>',
        html,
        re.I,
    )
    if desc:
        with_breaks = re.sub(r"<\s*br\s*/?>", "\n", desc.group(1), flags=re.I)
        with_breaks = re.sub(
            r"</(p|li|ul|ol|div|h\d)>", "\n", with_breaks, flags=re.I
        )
        description = (
            re.sub(r"\n{3,}", "\n\n", _decode(re.sub(r"<[^>]+>", " ", with_breaks)))
            .strip()
            or None
        )

    criteria: dict[str, str] = {}
    for cm in re.finditer(
        r'class="description__job-criteria-subheader"[^>]*>([\s\S]*?)</h3>'
        r'[\s\S]*?class="description__job-criteria-text[^"]*"[^>]*>([\s\S]*?)</span>',
        html,
        re.I,
    ):
        criteria[_clean(cm.group(1)).lower()] = _clean(cm.group(2))

    apply_m = re.search(
        r'class="topcard__link[^"]*"[^>]*href="([^"]+)"', html, re.I
    )
    apply_url = _decode(apply_m.group(1)).split("?")[0] if apply_m else None

    return {
        "id": job_id,
        "title": _clean(title_m.group(1)) if title_m else "(untitled)",
        "company": company,
        "company_url": company_url,
        "location": location,
        "date": None,
        "url": f"https://www.linkedin.com/jobs/view/{job_id}",
        "description": description,
        "seniority": criteria.get("seniority level"),
        "employment_type": criteria.get("employment type"),
        "job_function": criteria.get("job function"),
        "industries": criteria.get("industries"),
        "apply_url": apply_url,
    }


class LinkedInSource(JobSource):
    name = "linkedin"

    def __init__(self, max_pages: int | None = None):
        self.max_pages = max_pages if max_pages is not None else config.LINKEDIN_MAX_PAGES
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _fetch(self, url: str) -> str:
        delay = 0.5
        for attempt in range(7):
            try:
                resp = self._session.get(url, timeout=30, allow_redirects=True)
            except requests.RequestException as e:
                raise RuntimeError(f"LinkedIn fetch failed: {e}") from e
            if resp.status_code == 404:
                return ""
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == 6:
                    raise RuntimeError(
                        f"LinkedIn request failed: {resp.status_code} {resp.reason}"
                    )
                time.sleep(delay + random.uniform(0, 0.5))
                delay = min(delay * 2, 8)
                continue
            if not resp.ok:
                raise RuntimeError(
                    f"LinkedIn request failed: {resp.status_code} {resp.reason}"
                )
            return resp.text
        raise RuntimeError("LinkedIn request failed after retries")

    def _throttle(self) -> None:
        time.sleep(2.0 + random.uniform(0, 2.0))

    def detail(self, job_id: str) -> dict:
        html = self._fetch(f"{DETAIL_URL}/{job_id}")
        if not html:
            return {}
        return parse_job_detail(html, job_id)

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
        loc = location or "Remote"
        work_flag = _work_type_flag("remote" if "remote" in loc.lower() else None)
        tpr = _jobage_to_tpr(days)

        for q in queries:
            emit(f"[linkedin] search q={q!r} location={loc!r}…")
            page_hits = 0
            for page in range(self.max_pages):
                if page_hits >= limit:
                    break
                params: dict[str, Any] = {
                    "keywords": q,
                    "location": loc,
                    "start": page * 10,
                }
                if tpr:
                    params["f_TPR"] = tpr
                if work_flag:
                    params["f_WT"] = work_flag
                url = f"{SEARCH_URL}?{urlencode(params)}"
                try:
                    html = self._fetch(url)
                except Exception as e:
                    emit(f"[linkedin] ! {e}")
                    break
                cards = parse_job_cards(html)
                if not cards:
                    break
                emit(f"[linkedin] page {page + 1}: {len(cards)} card(s)")
                for card in cards:
                    jid = card["id"]
                    if jid in seen:
                        continue
                    seen.add(jid)
                    page_hits += 1
                    self._throttle()
                    try:
                        detail = self.detail(jid)
                    except Exception as e:
                        emit(f"[linkedin] ! detail {jid}: {e}")
                        detail = {}
                    job = self._to_job(card, detail)
                    if job:
                        out.append(job)
                    if page_hits >= limit:
                        break
                self._throttle()
        return out

    def _to_job(self, card: dict, detail: dict) -> dict | None:
        title = (detail.get("title") or card.get("title") or "").strip()
        if not title or title == "(untitled)":
            title = (card.get("title") or "").strip()
        if not title:
            return None
        link = detail.get("apply_url") or detail.get("url") or card.get("url")
        description = detail.get("description") or title
        skills: list[str] = []
        # Light keyword harvest from description for matcher
        blob = (description or "").lower()
        for kw in (
            "python", "javascript", "typescript", "react", "node", "fastapi",
            "django", "postgresql", "aws", "docker", "sql", "api",
        ):
            if kw in blob:
                skills.append(kw)

        return {
            "company": detail.get("company") or card.get("company") or "Unknown",
            "title": title,
            "location": detail.get("location") or card.get("location") or "Remote",
            "salary": None,
            "experience": detail.get("seniority"),
            "skills": skills,
            "link": link,
            "apply_method": "url",
            "apply_target": link,
            "description": description,
            "market": "foreign",
            "source": "linkedin",
        }
