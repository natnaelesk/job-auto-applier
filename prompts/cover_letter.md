# Cover letter for a job application

Write an honest one-page cover letter for the candidate.
Use ONLY the profile, answer bank, and CV facts. Do not invent experience.

Return ONLY JSON (no fences):

{
  "candidate_name": "full name",
  "contact_line": "email | phone | city | portfolio (one line)",
  "date": "Month Day, Year",
  "greeting": "Dear Hiring Team," or "Dear [Name]," if known,
  "paragraphs": [
    "opening paragraph...",
    "middle paragraph with relevant skills/projects...",
    "closing paragraph with availability / ask to review CV..."
  ],
  "closing": "Sincerely,"
}

Rules:
- 3 short paragraphs max (about 180-280 words total).
- ~1 year professional experience — never claim multi-year tenure.
- Mention the exact role title and company.
- Backend / full-stack strengths when relevant (TypeScript, React, Node, etc. from profile).
- If HUMAN NOTE asks for extras (tone, emphasis), follow it.
- No em dashes.
- Suitable to upload as a PDF cover letter on Google Forms.

CANDIDATE PROFILE / ANSWERS:
---
{profile}
---

CV TEXT:
---
{cv_text}
---

JOB:
Company: {company}
Title: {title}
Location: {location}
Description: {description}
---

HUMAN NOTE:
---
{user_note}
---
