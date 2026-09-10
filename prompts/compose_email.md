# Application email draft

Write a short, honest, calm job-application email for the candidate.
Use ONLY the profile and answers. Do not invent experience.

Follow **CV WRITING SKILL** letter/email rules. Profile Years / Matching rules /
Hard rules override defaults.

## Output

Return ONLY JSON (no fences):

{
  "subject": "short subject line",
  "body": "plain text email body, 120-220 words",
  "confidence": "high|medium|low"
}

## Rules

- Address the hiring team / company by name when known.
- Mention the exact role title from the job (not a guessed alternate title).
- **Years / seniority:** from the profile only — never invent multi-year tenure.
- Ask them to find the CV attached (the agent will attach it).
- Sign with the candidate's **full name from the profile**, plus email and
  portfolio/github links that appear in the profile. Never invent a signature name.
- **No unsolicited salary.** No em dashes (U+2014) or en dashes (U+2013).
- Location / visa / relocate only if Matching rules or the answer bank allow
  volunteering that detail.

## CV WRITING SKILL

---
{cv_writing_skill}
---

## CANDIDATE PROFILE

---
{profile}
---

## ANSWER BANK

---
{answers}
---

## JOB

---
To: {to_email}
Company: {company}
Title: {title}
Location: {location}
Description: {description}
CV path (for agent upload): {cv_path}
---
