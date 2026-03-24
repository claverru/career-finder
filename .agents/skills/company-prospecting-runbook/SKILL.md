---
name: company-prospecting-runbook
description: Discover and verify cold-outreach company prospects from the canonical CV text, confirmed preferences, and public company evidence. Use when Codex needs to find promising companies without relying on published vacancies, identify the best public contact channel or person, rank prospects, or update separate prospecting state.
---

# Company Prospecting Runbook

Use this skill for company prospecting, cold-outreach targeting, contact resolution, and separate prospecting state.

## Workflow

1. Read `/workspaces/job/career/AGENTS.md` and `/workspaces/job/career/prospecting/policy/workflow.md`.
2. Load `cv_plain.txt`, `profile.yaml`, `career/state/prospecting/prospects.jsonl`, `career/state/prospecting/contacts.jsonl`, `career/state/prospecting/runs.jsonl`, and `career/state/memory_review.jsonl`.
3. Run `scripts/build_prospect_brief.py`. Ask only when a blocking geography or remote preference is missing; persist confirmed answers with `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py`.
4. Derive the prospecting plan with `scripts/plan_prospect_run.py`, adding `--theme` only when the user explicitly asks for a thematic focus such as AI.
5. Prefer `scripts/run_prospect_pipeline.py` for normal runs. Use `scripts/sync_prospect_state.py` after updating prospecting Markdown batches.
6. Validate the company first, then resolve the best public contact. Prefer recruiting or hiring contacts, then relevant team leads or similar roles, then founders only when the public evidence suggests a lean or founder-led structure, and finally a verified public channel.
7. Keep the prospect ledger separate from job search. Deduplicate on `company + target_role_family`.

## Read only if needed

- `references/prospect-state.md` for ledger field intent
- `references/source-adapters.md` for supported source kinds and contact rules

## Validation

- `python scripts/build_prospect_brief.py`
- `python scripts/run_prospect_pipeline.py --source-catalog /workspaces/job/career/prospecting/policy/source_catalog.yaml`
- `python scripts/sync_prospect_state.py`
