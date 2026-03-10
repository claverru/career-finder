# Job Search Workflow Policy

This file defines the stable search workflow. Candidate facts must come from `/workspaces/job/career/profile/cv_plain.txt`. Personal preferences and confirmed memory must come from `/workspaces/job/career/profile/profile.yaml`, not from this document.

## Required inputs

Load these before searching or updating results:

- `/workspaces/job/career/profile/cv_plain.txt`
- `/workspaces/job/career/profile/profile.yaml`
- `/workspaces/job/career/search/state/jobs.jsonl`
- `/workspaces/job/career/search/state/applications.jsonl`
- `/workspaces/job/career/state/memory_review.jsonl`

## Decision contract

- Use only confirmed preferences from `profile.yaml` as hard filters or ranking signals.
- If a needed preference is missing or null, ask once and persist the answer in `profile.yaml`.
- Do not convert ambiguous historical notes into confirmed memory without explicit confirmation.

## Workflow

1. Load candidate context
   Read the canonical candidate profile text, confirmed preferences, confirmed memory, existing ledgers, and the review queue.
2. Build search intent from profile
   Derive role targets, positive keywords, and domain cues from `cv_plain.txt` and confirmed search preferences.
3. Discover opportunities
   Prefer recent discovery through LinkedIn public jobs and direct company boards.
   Use aggregators only for discovery, never as the final apply URL.
4. Resolve the direct apply link
   Prefer company-hosted Greenhouse, Lever, Workday, ApplyToJob, or official careers pages.
   Keep the discovery URL separately if needed, but only persist a direct company URL as `final_company_apply_url`.
5. Apply confirmed filters
   Reject roles that fail confirmed hard constraints, including:
   - remote mismatch,
   - contract mismatch,
   - Spain hiring mismatch,
   - missing model-development scope,
   - missing production ownership.
6. Capture evidence
   For every kept role, store quotes or direct evidence for remote policy, contract type, Spain hiring, modeling scope, deployment scope, and salary.
7. Capture compensation
   Prefer salary evidence in this order:
   - explicit salary on the final company page,
   - structured metadata on the company page,
   - explicit salary on the discovery page for the same live role,
   - external compensation sources,
   - inferred market band, clearly labeled as inferred.
8. Rank and annotate
   Use confirmed preferences for consulting risk, domain affinity, geography, and company memory.
   Keep subjective or ambiguous conclusions as narrative notes or review candidates, not as hard filters.
9. Persist outputs
   Write both:
   - a human-readable Markdown batch under `/workspaces/job/career/search/batches/`,
   - structured updates to `jobs.jsonl`, `applications.jsonl`, and optionally `memory_review.jsonl`.

## Invariants

- Never store an aggregator URL as the final apply link.
- Never add a duplicate role already present in `jobs.jsonl`.
- Never present inferred salary as explicit salary.
- Never use unconfirmed memory as a definitive reject signal.
- Default consulting risk to the confirmed allowed set from `profile.yaml`.
- Keep the Markdown batches readable and parseable because the ledger rebuild script uses them as input.

## Output fields

Every stored role should support these fields:

- `dedupe_key`
- `company`
- `role`
- `batch_id`
- `source_date`
- `posted_date`
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

Field intent:

- `user_note` keeps the raw human comment.
- `review_reason` explains why that comment still requires confirmation before becoming memory or a hard filter.
