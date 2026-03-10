# Search State Schema

## `jobs.jsonl`

One normalized job record per line.

Required fields:

- `dedupe_key`
- `company`
- `role`
- `batch_id`
- `source_date`
- `status`
- `discovery_url`
- `final_company_apply_url`
- `remote_policy_quote`
- `contract_type_signal`
- `spain_hiring_quote`
- `deep_learning_scope_quote`
- `deployment_scope_quote`
- `salary_band`
- `salary_basis`
- `salary_confidence`
- `salary_evidence`
- `consulting_risk`
- `user_note`
- `review_required`
- `review_reason`

Interpretation:

- `user_note` is the raw human comment captured from the batch.
- `review_reason` is the normalized operational reason for keeping that note in review instead of promoting it to confirmed memory.

## `applications.jsonl`

One application-state event per line.

Recommended fields:

- `dedupe_key`
- `company`
- `role`
- `status`
- `source_batch_id`
- `recorded_on`
- `note`

## `memory_review.jsonl`

One pending memory or preference candidate per line.

Recommended fields:

- `candidate_type`
- `scope`
- `value`
- `source_note`
- `review_reason`
- `company`
- `role`
- `source_batch_id`
- `status`

Use `status: pending_review` until the user confirms it.
