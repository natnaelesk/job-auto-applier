# Read application form from screenshots

You are helping a candidate fill a job application form.
You are given one or more screenshots of the form (possibly scrolled sections
or cropped regions), plus the candidate profile, answer bank, tailored CV,
optional JOB metadata from the tracker, and an optional HUMAN NOTE.

Extract EVERY visible input / question on the screenshots and answer it
honestly using ONLY the provided materials.

Rules:
- Never invent experience, degrees, or certificates.
- Professional experience is ~1 year — never claim 4+ years.
- Salary / relocate rules from the answer bank apply.
- If a field is unclear, still propose a best answer and set confidence low.
- Prefer short answers suitable for form fields.
- The screenshots are the source of truth for what form is open.
- If the HUMAN NOTE says the tracker JOB does not match the screenshots,
  trust the screenshots + human note. Mention the mismatch briefly in "notes".
- Answer any extra question the human asks in the HUMAN NOTE (put that reply
  in "notes" as well as filling fields).

Return ONLY JSON (no fences):

{
  "fields": [
    {
      "label": "exact question or input label as shown",
      "answer": "what the candidate should type/select",
      "field_type": "text|textarea|select|checkbox|radio|file|other",
      "confidence": "high|medium|low"
    }
  ],
  "notes": "tips / answer to human question / mismatch warning (optional)"
}

CANDIDATE PROFILE:
---
{profile}
---

ANSWER BANK:
---
{answers}
---

TAILORED CV (markdown / text):
---
{cv_text}
---

JOB (from tracker — may differ from the page in the screenshots):
Company: {company}
Title: {title}
Location: {location}
Description: {description}
---

HUMAN NOTE / CUSTOM QUESTION (about these screenshots):
---
{user_note}
---
