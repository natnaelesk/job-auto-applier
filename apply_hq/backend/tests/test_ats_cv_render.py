"""ATS CV renderer smoke tests — Times layout, no gold shop style."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import pdf_render  # noqa: E402


SAMPLE = {
    "name": "Natnael Eskinder Mengistu",
    "title": "Backend Engineer",
    "contact": {
        "email": "natnael@example.com",
        "phone": "+251000000000",
        "location": "Addis Ababa",
        "linkedin": "linkedin.com/in/example",
        "github": "github.com/example",
    },
    "summary": "Backend engineer focused on Python APIs and reliable systems.",
    "skills": [
        {"category": "Languages", "items": ["Python", "TypeScript"]},
        {"category": "Backend", "items": ["FastAPI", "Postgres"]},
    ],
    "experience": [
        {
            "role": "Software Engineer",
            "company": "Example Co",
            "period": "2024 - Present",
            "location": "Remote",
            "bullets": ["Built APIs", "Shipped features"],
        }
    ],
    "projects": [
        {
            "name": "Apply HQ",
            "description": "Manual apply desk for Notion queues.",
            "tech": ["Python", "React"],
        }
    ],
    "education": [
        {
            "degree": "B.Sc. Computer Science",
            "school": "Example University",
            "period": "2020 - 2024",
            "detail": "CGPA 3.8",
        }
    ],
    "languages": ["Amharic (native)", "English (fluent)"],
    "certificates": ["AWS Cloud Practitioner"],
}


def test_ats_name_stem():
    assert pdf_render.ats_name_stem("Natnael Eskinder Mengistu") == "NatnaelEskinder"
    assert pdf_render.ats_name_stem("Ada Lovelace") == "AdaLovelace"


def test_cv_output_path_ats_naming(tmp_path):
    p = pdf_render.cv_output_path(
        "Acme Corp",
        "Backend Engineer",
        tmp_path,
        full_name="Natnael Eskinder Mengistu",
    )
    assert p.name == "NatnaelEskinder_Acme_Corp_Backend_Engineer.pdf"


def test_render_cv_pdf_ats_writes_file(tmp_path):
    out = tmp_path / "NatnaelEskinder_Acme_Backend_Engineer.pdf"
    pdf_render.render_cv_pdf(SAMPLE, out)
    assert out.exists()
    assert out.stat().st_size > 500
    # Module must not use the old gold accent
    src = Path(pdf_render.__file__).read_text(encoding="utf-8")
    assert "b8860b" not in src
    assert "Times-Bold" in src
    assert "Times-Roman" in src
    assert "Times-Italic" in src
    assert "letter" in src
