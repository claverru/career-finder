# Search State

## `jobs.jsonl`

One canonical role per line. Core fields:

- identity and source: `dedupe_key`, `company`, `role`, `batch_id`, `source_date`, `source_kind`, `source_record_id`
- status and links: `status`, `discovery_url`, `final_company_apply_url`, `evidence_urls`
- fit evidence: `remote_policy_quote`, `contract_type_signal`, `spain_hiring_quote`, `deep_learning_scope_quote`, `deployment_scope_quote`
- compensation: `salary_band`, `salary_basis`, `salary_confidence`, `salary_evidence`
- notes and review: `user_note`, `review_required`, `review_reason`
- bookkeeping: `first_seen_at`, `last_seen_at`, `search_run_id`, `verification_confidence`

Field intent:

- `user_note` keeps the raw human comment
- `review_reason` explains why that comment still needs confirmation

## `search_runs.jsonl`

One staged run per line: `search_run_id`, `plan_id`, `seed_fingerprint`, `query_plan`, `sources_consulted`, `counts`, `status`, `reasons`, `reused_run_id`.

## `applications.jsonl`

One application event per line: `dedupe_key`, `company`, `role`, `status`, `source_batch_id`, `recorded_on`, `note`.

## `memory_review.jsonl`

One pending memory candidate per line: `candidate_type`, `scope`, `value`, `source_note`, `review_reason`, `company`, `role`, `source_batch_id`, `status`.

Use `pending_review` until the user confirms it.
