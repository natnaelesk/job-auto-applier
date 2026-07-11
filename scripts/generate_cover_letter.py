"""Generate a cover letter + experience PDF for a job application."""
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_fdre_mesob_cover_letter() -> Path:
    out_dir = PROJECT_ROOT / "output" / "cvs" / "cover letter"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "CoverLetter_Natnael_FDRE_MESOB_Center.pdf"

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=4 * mm,
        alignment=TA_JUSTIFY,
    )
    heading = ParagraphStyle(
        "heading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceAfter=2 * mm,
    )
    subheading = ParagraphStyle(
        "subheading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        spaceBefore=3 * mm,
        spaceAfter=1 * mm,
    )
    small = ParagraphStyle(
        "small", parent=styles["Normal"], fontSize=10, leading=13, spaceAfter=2 * mm
    )
    bullet = ParagraphStyle(
        "bullet",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        leftIndent=8 * mm,
        spaceAfter=1.5 * mm,
    )

    story = [
        Paragraph("Natnael Eskinder Mengistu", heading),
        Paragraph(
            "Addis Ababa, Ethiopia | natnaeleskinder41@gmail.com | +251975086006",
            small,
        ),
        Paragraph(
            "linkedin.com/in/natnaelesk | github.com/natnaelesk | natnaelesk.com",
            small,
        ),
        Spacer(1, 4 * mm),
        Paragraph("FDRE MESOB Center", small),
        Paragraph("Re: Backend Developer Application", small),
        Spacer(1, 4 * mm),
        Paragraph("Dear Hiring Team,", body),
        Paragraph(
            "I am writing to apply for the Backend Developer position at FDRE MESOB Center. "
            "I am a full-stack engineer based in Addis Ababa with about one year of professional "
            "experience building production backend systems, APIs, and databases for web and mobile products.",
            body,
        ),
        Paragraph(
            "At MMI Technology Solutions, I work as a solo engineer shipping client products end-to-end. "
            "On the backend, I have built and maintained REST APIs, database schemas, and deployment pipelines "
            "for a Somali e-commerce marketplace (web and mobile apps live in both stores), a business directory "
            "platform, and integrations for Hawkeye — a government accountability platform delivered to the "
            "Kenyan government. Python (Django and FastAPI) and Node.js are my primary backend stacks, with "
            "PostgreSQL and Supabase for data layers.",
            body,
        ),
        Paragraph(
            "I hold a B.Sc. in Computer Science from Ambo University (graduated March 2026, CGPA 3.65/4.0, "
            "English-medium instruction). I am motivated to contribute to public-service technology that "
            "improves access and efficiency for citizens, and I am available to start immediately.",
            body,
        ),
        Paragraph("Thank you for your consideration.", body),
        Spacer(1, 2 * mm),
        Paragraph("Best regards,<br/>Natnael Eskinder Mengistu", body),
        Spacer(1, 6 * mm),
        Paragraph("RELEVANT EXPERIENCE", heading),
        Paragraph(
            "Senior Software Developer — MMI Technology Solutions (Remote, Kenya) | Sep 2025 – Present",
            subheading,
        ),
        Paragraph(
            "• Built backend, database, and CI/CD for Suuq e-commerce marketplace (solo): APIs, PostgreSQL, deployment and DNS.",
            bullet,
        ),
        Paragraph(
            "• Developed full backend and database design for GlobalBizDir business directory platform.",
            bullet,
        ),
        Paragraph(
            "• Backend developer and integration work on Hawkeye (hawkeyekenya.com), tracking 10,000+ government projects across 47 counties.",
            bullet,
        ),
        Paragraph(
            "• Delivered Agunta Construction web app backend with Supabase, mail service, and SEO integration.",
            bullet,
        ),
        Paragraph(
            "IT Support Specialist (Intern) — Harar Health Office | Jun 2024 – Sep 2024",
            subheading,
        ),
        Paragraph(
            "• Deployed hospital management systems (Bahmni, TenaCare) across 16 hospitals; independently handled 2 sites, cutting project timeline from 4 to 2.5 months.",
            bullet,
        ),
        Paragraph(
            "Education: B.Sc. Computer Science, Ambo University — CGPA 3.65/4.0, graduated 13 March 2026",
            subheading,
        ),
        Paragraph(
            "Skills: Python, Django, FastAPI, Node.js, REST APIs, PostgreSQL, Supabase, Docker basics, CI/CD, AWS/Railway/Vercel deployment",
            bullet,
        ),
    ]

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    doc.build(story)
    return out_path


if __name__ == "__main__":
    path = generate_fdre_mesob_cover_letter()
    print(path)
