"""Smoke tests for locked Mik / Spark Notion property mapping.

Uses mocked Notion page payloads — no network required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.mapping import (  # noqa: E402
    ACTION_STATUS,
    MIK_PROPS,
    MIK_STATUS,
    SPARK_PROPS,
    SPARK_STATUS,
    build_cover_update,
    build_cv_update,
    build_status_update,
    needs_cv_filter,
    parse_page,
    queue_filter,
)


def _title(text: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": text}, "plain_text": text}]}


def _rich(text: str) -> dict:
    return {
        "rich_text": [
            {"type": "text", "text": {"content": text}, "plain_text": text}
        ]
    }


def _select(name: str | None) -> dict:
    return {"select": {"name": name} if name else None}


def _url(u: str | None) -> dict:
    return {"url": u}


def _check(v: bool) -> dict:
    return {"checkbox": v}


def _num(n) -> dict:
    return {"number": n}


def _date(start: str | None) -> dict:
    return {"date": {"start": start} if start else None}


def test_mik_prop_names_locked():
    assert MIK_PROPS["name"] == "Name"
    assert MIK_PROPS["company"] == "Company"
    assert MIK_PROPS["role"] == "Role"
    assert MIK_PROPS["status"] == "Status"
    assert MIK_PROPS["apply_link"] == "Apply link"
    assert MIK_PROPS["why"] == "Why keep"
    assert MIK_PROPS["has_cv"] == "Has CV"
    assert MIK_PROPS["cv_path"] == "CV path"
    assert MIK_PROPS["cover_letter"] == "Cover letter"
    assert MIK_PROPS["applied_date"] == "Applied date"
    assert MIK_PROPS["local_id"] == "Local id"
    assert "Found" in MIK_STATUS and "Offer" in MIK_STATUS
    assert "Won" not in MIK_STATUS


def test_spark_prop_names_locked():
    assert SPARK_PROPS["client"] == "Client"
    assert SPARK_PROPS["platform"] == "Platform"
    assert SPARK_PROPS["why"] == "Why it fits"
    assert SPARK_PROPS["budget"] == "Budget"
    assert SPARK_PROPS["package"] == "Package"
    assert SPARK_PROPS["local_id"] == "Local id"  # text on Spark
    assert "Won" in SPARK_STATUS and "Lost" in SPARK_STATUS
    assert "Interview" not in SPARK_STATUS


def test_parse_mik_page():
    page = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "url": "https://www.notion.so/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "properties": {
            "Name": _title("Acme — Backend Engineer"),
            "Company": _rich("Acme"),
            "Role": _rich("Backend Engineer"),
            "Status": _select("Ready"),
            "Apply link": _url("https://example.com/apply"),
            "Source": _select("WWR"),
            "Location": _rich("Remote"),
            "Remote": _check(True),
            "Stack": _rich("Python, FastAPI"),
            "Salary": _rich("$120k"),
            "Why keep": _rich("Good fit"),
            "CV path": _rich("/tmp/CV_Nat_Acme.pdf"),
            "Has CV": _check(True),
            "Cover letter": _rich(""),
            "Applied date": _date(None),
            "Local id": _num(42),
            "Notes": _rich("see JD"),
        },
    }
    row = parse_page("mik", page)
    assert row["board"] == "mik"
    assert row["company"] == "Acme"
    assert row["role"] == "Backend Engineer"
    assert row["status"] == "Ready"
    assert row["apply_link"] == "https://example.com/apply"
    assert row["has_cv"] is True
    assert row["cv_path"] == "/tmp/CV_Nat_Acme.pdf"
    assert row["local_id"] == 42
    assert row["remote"] is True
    assert row["source"] == "WWR"


def test_parse_spark_page():
    page = {
        "id": "11111111-2222-3333-4444-555555555555",
        "url": "https://www.notion.so/11111111222233334444555555555555",
        "properties": {
            "Name": _title("Landing page redesign"),
            "Client": _rich("Globex"),
            "Platform": _select("Upwork"),
            "Status": _select("Ready"),
            "Apply link": _url("https://upwork.com/jobs/1"),
            "Budget": _rich("$500"),
            "Stack": _rich("React"),
            "Package": _rich("Web"),
            "Why it fits": _rich("Portfolio match"),
            "CV path": _rich(""),
            "Has CV": _check(False),
            "Cover letter": _rich(""),
            "Applied date": _date(None),
            "Local id": _rich("spark-7"),
            "Notes": _rich(""),
        },
    }
    row = parse_page("spark", page)
    assert row["board"] == "spark"
    assert row["client"] == "Globex"
    assert row["company"] == "Globex"
    assert row["platform"] == "Upwork"
    assert row["has_cv"] is False
    assert row["local_id"] == "spark-7"
    assert row["budget"] == "$500"


def test_build_status_applied_sets_date():
    props = build_status_update("mik", "Applied", notes="sent")
    assert props["Status"]["select"]["name"] == "Applied"
    assert props["Applied date"]["date"]["start"]
    assert props["Notes"]["rich_text"][0]["text"]["content"] == "sent"


def test_build_status_closed_no_date():
    props = build_status_update("spark", "Closed")
    assert props["Status"]["select"]["name"] == "Closed"
    assert "Applied date" not in props


def test_build_cv_update():
    props = build_cv_update("mik", "/out/CV_A_B.pdf")
    assert props["CV path"]["rich_text"][0]["text"]["content"] == "/out/CV_A_B.pdf"
    assert props["Has CV"]["checkbox"] is True


def test_build_cover_update():
    props = build_cover_update("spark", "/out/cover.pdf")
    assert "Cover letter" in props


def test_action_status_rejected_invalid():
    with pytest.raises(ValueError):
        build_status_update("mik", "Rejected")


def test_queue_and_needs_cv_filters():
    q = queue_filter()
    assert q["property"] == "Status"
    assert q["select"]["equals"] == "Ready"
    n = needs_cv_filter()
    assert n["property"] == "Has CV"
    assert n["checkbox"]["equals"] is False


def test_action_status_set():
    assert ACTION_STATUS == {"Applied", "Closed", "Later"}
