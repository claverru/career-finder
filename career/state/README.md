# Career State

Canonical local state now lives under a single root: `/workspaces/job/career/state/`.

- Shared review queue: `memory_review.jsonl`
- Search state: `search/jobs.jsonl`, `search/applications.jsonl`, `search/runs.jsonl`, `search/compact_jobs.md`
- Prospecting state: `prospecting/prospects.jsonl`, `prospecting/contacts.jsonl`, `prospecting/runs.jsonl`

Generated discovery and ranking artifacts also stay under the matching subdirectory so search and prospecting each have one predictable state home.
