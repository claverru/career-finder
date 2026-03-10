---
name: job-search-runbook
description: Discover, verify, and track job opportunities using the canonical candidate profile text, confirmed preferences, and structured search state. Use when Codex needs to search for roles, validate remote and Spain-hiring fit, capture salary evidence, dedupe opportunities, migrate or update search ledgers, or turn historical notes into reviewable memory instead of hardcoded preferences.
---

# Job Search Runbook

## Workflow

1. Read `/workspaces/job/career/profile/cv_plain.txt`.
2. Read `/workspaces/job/career/profile/profile.yaml`.
3. If those local files are missing in a clean clone, seed them from `/workspaces/job/career/profile/cv_plain.example.txt` and `/workspaces/job/career/profile/profile.example.yaml`.
4. Read `/workspaces/job/career/search/policy/workflow.md`.
5. Read `/workspaces/job/career/search/state/jobs.jsonl`, `/workspaces/job/career/search/state/applications.jsonl`, and `/workspaces/job/career/state/memory_review.jsonl`.
6. Build filters and ranking from confirmed preferences only.
7. If a high-impact preference is missing, ask once and persist it. Use `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py` when the answer becomes confirmed profile data.
8. Keep ambiguous historical notes in the review queue.
9. Persist both human-readable Markdown batches and structured JSONL records.

## Guardrails

- Never keep an aggregator URL as the final apply link.
- Never use unconfirmed memory as a definitive reject rule.
- Never present inferred salary as explicit.
- Never create a duplicate canonical job record for the same `dedupe_key`.

## Repo resources

- Search workflow reference: `references/search-workflow.md`
- Search state schema: `references/search-state.md`
- Confirmed preference writer: `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py`
- Ledger rebuild script: `scripts/sync_search_state.py`

## Typical tasks

- Search for new roles using confirmed preferences.
- Verify remote, Spain hiring, contract, and production-ML scope.
- Capture salary evidence and label it correctly.
- Update the job ledger and application ledger.
- Import old narrative batches and extract reviewable memory.

## Validation

- Run `python scripts/sync_search_state.py` when Markdown batches change or the ledgers need to be rebuilt from source files.
- Review `memory_review.jsonl` before promoting any candidate preference into confirmed memory.
