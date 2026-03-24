# Company Prospecting Workflow Policy

Candidate facts come from `career/profile/cv_plain.txt`. Confirmed preferences and memory come from `career/profile/profile.yaml`.

## Inputs

Load these before prospecting or state updates:

- `career/profile/cv_plain.txt`
- `career/profile/profile.yaml`
- `career/state/prospecting/prospects.jsonl`
- `career/state/prospecting/contacts.jsonl`
- `career/state/prospecting/runs.jsonl`
- `career/state/memory_review.jsonl`

## Decision contract

- use only confirmed preferences and confirmed memory as hard filters or ranking signals
- if a needed high-impact geography or remote preference is missing, ask once and persist it
- keep ambiguous notes in review until confirmed

## Staged flow

1. Build the mini brief. Block only on remote mode, base location, and hireable geography.
2. Derive the query plan from `cv_plain.txt` plus confirmed preferences: role families, topical focus, positive and negative keywords, location filters, company preferences, and source priority.
3. Discover candidate companies from public sources in this order: leaderboards, funding roundups, company directories, official company pages, public people pages, public LinkedIn company pages, and generic web fallback.
4. Verify the company first. Keep only prospects with enough evidence for company potential and role plausibility.
5. Apply the same geography rigor as job search. Use remote and hireable-geography evidence from official or public pages; discard clear mismatches and keep missing evidence as pending review.
6. Resolve the best public contact only after the company passes. Prefer recruiting or hiring contacts, then relevant team leads or similar roles, then founders only when the company appears lean or founder-led, then a verified public channel. Within comparable options, prefer verified public emails or LinkedIn profiles over X or generic contact pages.
7. Rank with interpretable sub-scores: `company_potential`, `role_plausibility`, `geography_fit`, `contactability`, and `evidence_quality`. When confirmed preferences say EU employers or Spain presence are preferred, reward those signals in the geography score.
8. Persist human-readable Markdown batches plus structured updates to `prospects.jsonl`, `contacts.jsonl`, `runs.jsonl`, and `memory_review.jsonl` when needed.

## Invariants

- never use a published vacancy as a requirement for keeping a prospect
- never create a duplicate canonical prospect for the same `company + target_role_family`
- never treat a guessed or inferred email as verified contact data
- never use unconfirmed memory as a reject rule
- keep Markdown batches readable because `sync_prospect_state.py` parses them
