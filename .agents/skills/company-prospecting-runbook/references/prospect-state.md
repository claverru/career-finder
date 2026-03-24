# Prospect State

Canonical prospecting state lives under `career/state/prospecting/`.

## `prospects.jsonl`

One canonical prospect per `company + target_role_family`. Core fields:

- identity and source: `dedupe_key`, `company`, `target_role_family`, `batch_id`, `source_kind`, `source_record_id`
- status and ranking: `status`, `total_score`, `company_potential_score`, `role_plausibility_score`, `geography_fit_score`, `contactability_score`, `evidence_quality_score`
- evidence: `rationale`, `company_potential_quote`, `role_plausibility_quote`, `geography_fit_quote`, `contactability_quote`, `evidence_urls`
- selected contact: `selected_contact_type`, `selected_contact`, `selected_contact_role`, `selected_contact_url_or_email`, `contact_confidence`
- bookkeeping: `first_seen_at`, `last_seen_at`, `prospect_run_id`, `verification_confidence`, `review_required`, `review_reason`

## `contacts.jsonl`

One selected contact per canonical prospect:

- identity: `contact_id`, `prospect_dedupe_key`, `company`, `target_role_family`
- contact payload: `contact_type`, `name_or_channel`, `role`, `contact_url_or_email`, `confidence`
- selection metadata: `selection_reason`, `evidence_urls`, `prospect_run_id`, `selected`

## `runs.jsonl`

One staged prospecting run per line: `prospect_run_id`, `plan_id`, `seed_fingerprint`, `query_plan`, `sources_consulted`, `counts`, `status`, `reasons`, `reused_run_id`.
