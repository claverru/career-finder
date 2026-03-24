# Career Domain Instructions

Canonical files:

- facts and reusable evidence: `/workspaces/job/career/profile/cv_plain.txt`
- staged import text: `/workspaces/job/career/profile/imported_resume.txt`
- confirmed preferences and memory: `/workspaces/job/career/profile/profile.yaml`
- search policy: `/workspaces/job/career/search/policy/workflow.md`
- search state: `/workspaces/job/career/state/search/jobs.jsonl`, `/workspaces/job/career/state/search/applications.jsonl`, and `/workspaces/job/career/state/search/runs.jsonl`
- prospecting policy: `/workspaces/job/career/prospecting/policy/workflow.md`
- prospecting state: `/workspaces/job/career/state/prospecting/prospects.jsonl`, `/workspaces/job/career/state/prospecting/contacts.jsonl`, and `/workspaces/job/career/state/prospecting/runs.jsonl`
- review queue: `/workspaces/job/career/state/memory_review.jsonl`

Rules:

- Keep the narrative CV only in `cv_plain.txt`; do not duplicate it into `profile.yaml`.
- If local files are missing, seed them from the matching `.example` files.
- If the user provides a resume file and `cv_plain.txt` is missing or stale, run `/workspaces/job/.agents/skills/cv-optimize/scripts/import_resume.py` first. OCR imports are review-first.
- Use only confirmed preferences and confirmed memory as hard filters or ranking signals.
- If a needed high-impact preference is missing, ask once and persist it with `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py`.
- Do not promote review-queue notes into confirmed memory without explicit confirmation.
- If a search or prospecting run uncovers a reusable workflow improvement, patch the smallest relevant local artifact before finishing the turn.
  This can be a domain policy, a skill reference, or a supporting script.
- Use `cv-optimize` for resume work, `job-search-runbook` for vacancy search and search state work, and `company-prospecting-runbook` for cold-outreach company prospecting.
