# CV Writing Skill (generic)

Reusable guidance for tailoring CVs, cover letters, and short application answers.
Load this skill together with the candidate's local profile files. It contains
**no candidate-specific biography** — only method.

## Source of truth (never invent)

Use ONLY facts from the candidate's local files, typically:

- `profile/master_cv.md` — experience, projects, skills, education, contact
- `profile/about_me.md` — identity, preferences, **Years / Matching rules / Hard rules**
- `profile/answers.md` — salary, visa, relocate, start date, reusable form answers

If a fact is missing, omit it or say you do not have it. Never invent URLs, employers,
job titles, dates, metrics, certificates, or years of experience.

**Years of experience:** read **Years**, **Seniority**, or **Matching rules** from the
profile. Do **not** hardcode phrases like "~1 year" or "2+ years" from this skill.

## ATS-clean CV structure

Preferred order on the page:

1. **Header** — name, role title tuned to the job, contact line
2. **Summary / Objective** — 2–3 sentences, role-matched voice from profile
3. **Experience** — most relevant roles first
4. **Projects** — 2–3 strongest for this job (from master CV only)
5. **Skills** — last among the core content blocks; job-required skills the
   candidate actually has come first within each category
6. **Education**, then **Languages**

Writing craft:

- Start bullets with strong action verbs (Built, Designed, Shipped, Led, Automated).
- Quantify **only** when the number appears in the source files. No invented metrics.
- No icons, emoji, skill chips, progress bars, or decorative graphics.
- **Never** use em dashes (—) or en dashes (–). Use commas, colons, or plain hyphens.
- Keep language calm and concrete. Avoid fluff ("passionate team player").
- Length: **1 page is fine** when content is thin; **1–2 pages are OK** when there is
  real substance. Prefer denser truth over padding empty space.

## Role flavor: what to lead with vs demote

Infer a flavor from the **job title + description**, then reorder experience/projects
so the strongest truthful fit leads. Demote (do not delete) weaker fits. Never invent
projects to fill a flavor.

| Flavor | Lead with (if present in master CV) | Demote / shorten |
|--------|--------------------------------------|------------------|
| **fullstack** | End-to-end apps, API + UI ownership, shipping full features | Narrow single-layer spikes unless they match the stack |
| **backend** | APIs, services, data, auth, infra, reliability | Pure UI polish / design-only work |
| **frontend** | UI systems, React/web clients, UX-facing delivery | Infra-only / DB-only deep dives |
| **mobile** | Mobile apps, store/release, device UX | Desktop-only or unrelated web admin |
| **ai** | ML/LLM features, data pipelines, evals, AI product work | Unrelated CRUD with no AI angle |
| **junior / early-professional** | Learning velocity, ownership of scoped features, internships, solid fundamentals | Inflated "senior" framing; do not claim lead/years you lack |
| **it_support** | Help desk, troubleshooting, tickets, hardware/software support, docs | Deep product-engineering narratives that hide support fit |

If the job mixes flavors (e.g. "Full-Stack + AI"), lead with the primary title word,
then the secondary stack from the description.

## Project catalog entry (shape)

When reading or summarizing a project from `master_cv.md`, keep this shape in mind:

- **Name** — exact name from the master CV
- **What it does** — one plain sentence
- **Ownership** — what the candidate actually owned (from source)
- **Stack** — tools listed in source only
- **Public URL** — only if present in profile/master CV; otherwise `"none"`
- **CV use** — when to feature it (e.g. "lead for backend/API roles")

### Project list (fill locally — or read from master_cv)

The model should prefer **Projects** already written in `master_cv.md`.
If the user maintains an optional local catalog, use placeholders like this
(never invent real client names here):

```text
- Name: [Project A]
  What: [one sentence]
  Ownership: [your role]
  Stack: [tools]
  Public URL: none
  CV use: [e.g. lead for fullstack]

- Name: [Project B]
  What: [one sentence]
  Ownership: [your role]
  Stack: [tools]
  Public URL: none
  CV use: [e.g. demote for it_support]
```

## Cover letters and short form answers

- Calm, email-style tone. Exact role title and company when known.
- Role-matched professional title consistent with the tailored CV.
- **No unsolicited salary** in letters/emails unless the form/human note asks.
- Location / relocate / visa: only as allowed by profile **Matching rules** /
  **Hard rules** and the answer bank — do not volunteer Africa volunteering,
  visa stories, or relocate pitches unless those rules say so.
- Years and seniority: from profile only.
- Short form answers: prefer the answer bank; keep replies form-field short.
- EEO / demographic / disability / gender / race questions: follow the answer
  bank; if missing, prefer "Prefer not to say" / decline patterns the bank uses —
  **do not invent demographics**.
- No em dashes.

## Anti-hallucination checklist (every generation)

- [ ] Every employer, school, project, URL, and metric appears in the source files
- [ ] Years / seniority match profile Matching rules (not this skill's imagination)
- [ ] Salary / visa / Easy Apply behavior follow answer bank + Hard rules
- [ ] No em/en dashes; no icons; no invented certificates
- [ ] Output shape matches the calling prompt's JSON schema exactly
