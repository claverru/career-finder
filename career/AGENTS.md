# Career Domain Instructions

Use this directory for profile management, resume optimization, and job search.

Primary files:

- Canonical local candidate facts: `/workspaces/job/career/profile/cv_plain.txt`
- Canonical local preferences and memory: `/workspaces/job/career/profile/profile.yaml`
- Example candidate facts seed: `/workspaces/job/career/profile/cv_plain.example.txt`
- Example preferences seed: `/workspaces/job/career/profile/profile.example.yaml`
- Rendered LaTeX resume: `/workspaces/job/career/profile/render/main.tex`
- Search workflow policy: `/workspaces/job/career/search/policy/workflow.md`
- Search ledgers: `/workspaces/job/career/search/state/jobs.jsonl` and `/workspaces/job/career/search/state/applications.jsonl`
- Review queue for ambiguous historical memory: `/workspaces/job/career/state/memory_review.jsonl`

Rules:

- Load `cv_plain.txt` before editing candidate facts, evidence, or CV content.
- Load `profile.yaml` before applying search filters or CV guardrails that depend on confirmed preferences or memory.
- If either local file is missing in a clean clone, copy the matching `.example` file first.
- Use only confirmed preferences from `profile.yaml` as hard filters or ranking preferences.
- If a needed preference is missing or `null`, ask once and persist it in `profile.yaml`.
- Prefer `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py` when persisting confirmed preferences or confirmed memory updates.
- Do not promote historical notes from the review queue into confirmed memory without user confirmation.
- Use `/workspaces/job/career/search/policy/workflow.md` as the stable search process; there is no extra nested `AGENTS.md` under `search/`.

Skills:

- Use the repo-local skill `cv-optimize` for resume review, tailoring, artifact sync, and evidence-gap analysis.
- Use the repo-local skill `job-search-runbook` for opportunity discovery, validation, dedupe, and state updates.
