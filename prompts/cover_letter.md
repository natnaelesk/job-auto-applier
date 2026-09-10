# Cover letter for a job application

Write an honest, calm, email-style one-page cover letter for the candidate.
Use ONLY the profile, answer bank, and CV facts. Do not invent experience.

Follow **CV WRITING SKILL** for tone, anti-hallucination, and letter rules.
Profile **Years / Matching rules / Hard rules** override defaults.

## Output

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

## Rules

- 3 short paragraphs max (about 180–280 words total).
- **Years / seniority:** read from the profile (Years, Seniority, Matching rules).
  Never invent multi-year tenure or hardcode a year count.
- Mention the exact role title and company.
- Match strengths to the job flavor using real stack/projects from the CV/profile
  (backend, fullstack, frontend, mobile, AI, IT support, etc.).
- Role-matched professional framing consistent with how the candidate presents
  themselves in the profile — not a generic "passionate engineer" opener.
- **No unsolicited salary.** Do not mention compensation unless HUMAN NOTE asks.
- Location / relocate / visa: only if profile Matching rules or answer bank allow
  volunteering that detail. Do not add visa, volunteering, or relocate pitches
  unless those sources say so.
- If HUMAN NOTE asks for extras (tone, emphasis), follow it.
- No em dashes (U+2014) or en dashes (U+2013).
- Suitable to upload as a PDF cover letter on Google Forms / ATS.

## Few-shot shape note (illustrative tone — not biography)

Opening: name the role + company, one honest fit sentence.
Middle: 1–2 sourced projects or experience bullets tied to the job.
Closing: availability from profile/answers + ask them to review the CV; sign-off
in JSON `closing` (name is rendered separately).

## CV WRITING SKILL

---
{cv_writing_skill}
---

## CANDIDATE PROFILE / ANSWERS

---
{profile}
---

## CV TEXT

---
{cv_text}
---

## JOB

Company: {company}
Title: {title}
Location: {location}
Description: {description}
---

## HUMAN NOTE

---
{user_note}
---
