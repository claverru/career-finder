# Search State

Canonical search state lives under `career/state/search/`.

## `jobs.jsonl`

One canonical role per line. Core fields:

- identity and source: `internal_job_id`, `dedupe_key`, `company`, `role`, `batch_id`, `source_date`, `source_kind`, `source_record_id`
- status and links: `status`, `discovery_url`, `final_company_apply_url`, `evidence_urls`
- fit evidence: `remote_policy_quote`, `contract_type_signal`, `spain_hiring_quote`, `deep_learning_scope_quote`, `deployment_scope_quote`
- compensation: `salary_band`, `salary_basis`, `salary_confidence`, `salary_evidence`
- notes and review: `user_note`, `review_required`, `review_reason`
- bookkeeping: `first_seen_at`, `last_seen_at`, `search_run_id`, `verification_confidence`

Field intent:

- `user_note` keeps the raw human comment
- when a note implies a concrete workflow state, persist that state explicitly in the batch as `User status`
- `status` in structured state should come from that explicit batch status when present
- allowed workflow states: `discovered`, `new`, `applied`, `interview`, `pending`, `discarded`
- `internal_job_id` is a stable repo-local id, normally derived from the canonical job link hash and preserved across later syncs
- `review_reason` explains why that comment still needs confirmation

## `runs.jsonl`

One staged run per line: `search_run_id`, `plan_id`, `seed_fingerprint`, `query_plan`, `sources_consulted`, `counts`, `status`, `reasons`, `reused_run_id`.

## `applications.jsonl`

One application event per line: `internal_job_id`, `dedupe_key`, `company`, `role`, `status`, `source_batch_id`, `recorded_on`, `note`.

## `compact_jobs.md`

A compact human-readable process ledger. One row per role with:

- `Internal Job ID`
- `Title`
- `Company`
- `Salary`
- `Status`

This file is regenerated from the persistent state and is safe to use as the compact view after old batches are deleted.

## `memory_review.jsonl`

One pending memory candidate per line: `candidate_type`, `scope`, `value`, `source_note`, `review_reason`, `company`, `role`, `source_batch_id`, `status`.

Use `pending_review` until the user confirms it.

## Retention model

- sync is additive: current batches can add or update state, but missing batches do not delete prior jobs from the persistent ledger
- after verifying the compact ledger, old batch files can be deleted to reduce clutter
- if a role should disappear from state, remove it manually from the persistent state rather than relying on batch absence
