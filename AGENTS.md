# Repository Instructions

Active domain: `career/`.

For work under `career/`, read `/workspaces/job/career/AGENTS.md` first.

Global rules:

- Candidate facts and reusable evidence live in `/workspaces/job/career/profile/cv_plain.txt`.
- Confirmed preferences and confirmed memory live in `/workspaces/job/career/profile/profile.yaml`.
- If either local file is missing, seed it from the matching `.example` file.
- If the user provides an external resume and `cv_plain.txt` is missing or stale, import it before deeper CV work.
- Never invent achievements, dates, technologies, salary expectations, or user preferences.
- If a missing high-impact preference blocks a decision, ask once and persist the answer.
- For serious search work, use the staged flow: brief, plan, official/public discovery, verification, ranking, persistence.
- Use confirmed memory as a filter or ranking signal; keep ambiguous notes in the review queue.
- Prefer repo-local skills under `/workspaces/job/.agents/skills/` over ad hoc prompts when the task matches them.
