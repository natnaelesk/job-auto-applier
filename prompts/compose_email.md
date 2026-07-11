# Application email draft

Write a short, honest job-application email for the candidate.
Use ONLY the profile and answers. Do not invent experience.

Return ONLY JSON (no fences):

{
  "subject": "short subject line",
  "body": "plain text email body, 120-220 words",
  "confidence": "high|medium|low"
}

Rules:
- Address the hiring team / company by name when known.
- Mention the exact role title.
- ~1 year professional experience — never claim multi-year tenure.
- Ask them to find the CV attached (the agent will attach it).
- Sign as Natnael Eskinder with email + portfolio/github from the profile.
- No em dashes.

CANDIDATE PROFILE:
---
{profile}
---

ANSWER BANK:
---
{answers}
---

JOB:
---
To: {to_email}
Company: {company}
Title: {title}
Location: {location}
Description: {description}
CV path (for agent upload): {cv_path}
---
