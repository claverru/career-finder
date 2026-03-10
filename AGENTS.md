# Repository Instructions

This repository has one active domain:

- `career/`: candidate profile data, resume artifacts, job-search workflow, and Codex skills.

For work under `career/`, always read `/workspaces/job/career/AGENTS.md` first.

Global rules:

- Treat `/workspaces/job/career/profile/cv_plain.txt` as the canonical local source of truth for candidate facts, resume content, and reusable evidence.
- Treat `/workspaces/job/career/profile/profile.yaml` as the canonical local source of truth for confirmed preferences and confirmed memory.
- If those local files are missing in a clean clone, seed them from `/workspaces/job/career/profile/cv_plain.example.txt` and `/workspaces/job/career/profile/profile.example.yaml`.
- Never invent achievements, dates, technologies, salary expectations, or user preferences.
- If a decision depends on a missing high-impact preference, ask once, then persist the answer in the canonical store.
- Use confirmed memory as a filter or ranking signal. Keep ambiguous historical notes in the review queue until they are confirmed.
- Prefer the repo-local skills under `/workspaces/job/.agents/skills/` over ad hoc prompts when the task matches them.
