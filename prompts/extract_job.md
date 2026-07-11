# Job Extraction Prompt (batch)

You are a job-post parser. Below are raw messages from a Telegram job channel.
The channel aggregates jobs from many sources, so formats vary wildly.
Messages may include a "[Source post]" section - that is the original posting
the aggregator linked to; prefer its details (especially application links).

For EACH message, extract its job(s). A message may contain ZERO jobs (ads,
channel announcements), ONE job, or MULTIPLE jobs.

Return ONLY a JSON object (no markdown fences, no commentary) mapping each
message id to an array of jobs:

{
  "12345": [ { ...job... } ],
  "12346": []
}

Each job object:

{
  "company": "string or null",
  "title": "string or null",
  "location": "string or null (e.g. 'Remote', 'Addis Ababa', 'Hybrid - Berlin')",
  "salary": "string or null (exactly as written)",
  "experience": "string or null (e.g. '2+ years', 'Senior', 'Entry level')",
  "skills": ["list", "of", "technologies/skills mentioned"],
  "link": "application URL or null",
  "apply_method": "url | email | telegram | unknown",
  "apply_target": "the URL, email address, or telegram handle to apply through",
  "description": "2-3 sentence summary of the role and requirements"
}

Rules:
- Include EVERY message id from the input in your output, even when its array is empty.
- Never invent information that is not in the message.
- For "link"/"apply_target": prefer a real application URL (careers page, form)
  over t.me links. A t.me link pointing at the original post is NOT an
  application link - if that's all there is, use apply_method "telegram" only
  when applicants are told to contact a telegram handle; otherwise "unknown".
- If multiple application methods exist, prefer: url > email > telegram.
- Keep salary/experience text exactly as written in the post.

MESSAGES:
---
{messages}
---
