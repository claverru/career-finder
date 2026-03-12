# Job Search Workflow Policy

Candidate facts come from `career/profile/cv_plain.txt`. Confirmed preferences and memory come from `career/profile/profile.yaml`.

## Inputs

Load these before search or state updates:

- `career/profile/cv_plain.txt`
- `career/profile/profile.yaml`
- `career/search/state/jobs.jsonl`
- `career/search/state/applications.jsonl`
- `career/state/memory_review.jsonl`

## Decision contract

- use only confirmed preferences and confirmed memory as hard filters or ranking signals
- if a needed preference is missing, ask once and persist it
- keep ambiguous historical notes in review until confirmed

## Staged flow

1. Build the mini brief. Block only on missing remote mode, base location, hireable geography, allowed contracts, model-development requirement, or production-ownership requirement.
2. Derive the query plan from `cv_plain.txt` plus confirmed preferences: role families, positive and negative keywords, location and contract filters, company and domain priority, source priority.
3. Discover from official or public sources in this order: Greenhouse, Lever, public Ashby boards, official careers pages, LinkedIn public discovery, generic web fallback.
4. Resolve a direct company apply URL. Aggregators and LinkedIn stay discovery-only.
5. Verify evidence for remote fit, hiring geography, contract type, modeling scope, deployment scope, and salary.
   For remote detection, do not rely only on the word `remote`: treat signals like `flexible workplace`, `work anywhere`, `virtual-Spain`, and country-level locations with workplace flexibility as valid remote evidence unless the posting also introduces hybrid or office requirements.
6. Capture salary in every kept role.
   If the official posting includes compensation, store it as `Explicit`.
   If it does not, infer a band from external public sources and store it as `Inferred` with evidence and confidence.
7. Rank with confirmed preferences and evidence strength.
   Modeling is the hard requirement. Production ownership is a plus unless the confirmed profile explicitly requires it. Reject pure MLOps or platform roles that do not show model-development scope.
8. Persist readable Markdown batches plus structured updates to `jobs.jsonl`, `applications.jsonl`, `search_runs.jsonl`, and `memory_review.jsonl` when needed.

## Invariants

- never store an aggregator URL as `final_company_apply_url`
- never create a duplicate `dedupe_key`
- never present inferred salary as explicit
- never use unconfirmed memory as a reject rule
- keep Markdown batches readable because `sync_search_state.py` parses them
