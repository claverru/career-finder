---
name: job-search-runbook
description: Discover, verify, and track job opportunities using the canonical candidate profile text, confirmed preferences, and structured search state. Use when Codex needs to search for roles, validate remote and Spain-hiring fit, capture salary evidence, dedupe opportunities, migrate or update search ledgers, or turn historical notes into reviewable memory instead of hardcoded preferences.
---

# Job Search Runbook

Use this skill for role discovery, verification, ranking, ledgers, and reviewable memory.

## Workflow

1. Read `/workspaces/job/career/AGENTS.md` and `/workspaces/job/career/search/policy/workflow.md`.
2. Load `cv_plain.txt`, `profile.yaml`, `state/search/jobs.jsonl`, `state/search/applications.jsonl`, `state/search/runs.jsonl`, and `state/memory_review.jsonl`.
3. Run `scripts/build_search_brief.py`. If blocking questions remain, ask only those and persist confirmed answers with `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py`.
4. Derive the plan with `scripts/plan_search_run.py`.
5. Prefer `scripts/run_search_pipeline.py` for normal runs. Use `scripts/run_source_discovery.py` and `scripts/verify_and_rank.py` only for partial reruns or debugging.
6. Always capture a salary band. Use the posting salary when present; otherwise infer a band from external public sources and label it `Inferred` with evidence and confidence.
7. For remote-only filtering, accept strong flexibility signals such as `flexible workplace` or country-level remote location wording; reject only clear hybrid, onsite, or office-bound roles.
8. Treat model development as the hard scope requirement. Production ownership is optional unless confirmed as required in `profile.yaml`. Reject pure MLOps or platform roles with no model-development evidence.
9. Keep aggregators discovery-only, keep unconfirmed memory out of hard filters, and never create duplicate `dedupe_key` records.
10. If Markdown batches change, rebuild structured state with `scripts/sync_search_state.py`.
    The sync is additive: it updates the persistent ledger from current batches, but does not delete prior roles just because a batch file disappeared.
11. If you discover a reusable search improvement while working, persist it in the smallest relevant local artifact before finishing.
    Examples: ATS API endpoints, stronger verification paths, better status-note parsing, or remote-detection heuristics.
12. If you add a human note such as `aplicado`, `en proceso`, or `esperando respuesta`, resolve its meaning semantically yourself and persist the result as an explicit `User status` field in the batch.
    Do not rely on the state-sync script to infer workflow status from free-form note wording.
13. Use the compact process ledger in `career/state/search/compact_jobs.md` when the user wants a compressed view, and regenerate it with `scripts/sync_search_state.py --compact-only` when needed.

## Read only if needed

- `references/search-state.md` for ledger field intent
- `references/source-adapters.md` for supported source kinds

## Validation

- `python scripts/build_search_brief.py`
- `python scripts/run_search_pipeline.py --source-catalog /workspaces/job/career/search/policy/source_catalog.yaml`
- `python scripts/sync_search_state.py`
- `python scripts/sync_search_state.py --compact-only`
