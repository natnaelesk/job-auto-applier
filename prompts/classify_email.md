# Classify company email replies

You match inbox emails to job applications the candidate already submitted.

For EACH email, decide:
- which job id it belongs to (or null if none)
- new status if this is a meaningful company response
- a one-line summary

Status values allowed:
- "interview" — invite to interview / next steps / assessment
- "rejected" — rejection / not moving forward
- "offer" — offer / compensation discussion clearly an offer
- "applied" — acknowledgment / "we received your application" (no status change needed beyond note)
- null — unrelated / newsletter / noise (ignore)

Return ONLY JSON:

{
  "results": [
    {
      "email_id": "gmail-message-id",
      "job_id": 17,
      "status": "interview",
      "summary": "Invited to a 30-min screening call next week"
    }
  ]
}

Include every email id from the input. Use job_id null and status null when unrelated.

APPLIED JOBS (id, company, title, link):
---
{jobs}
---

EMAILS:
---
{emails}
---
