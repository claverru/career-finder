# Search Workflow Reference

Policy source: `/workspaces/job/career/search/policy/workflow.md`

Use this skill to:

- discover opportunities,
- verify role fit and direct apply links,
- capture salary evidence,
- update ledgers,
- turn historical notes into review candidates instead of assumptions.

Mandatory inputs:

- `/workspaces/job/career/profile/cv_plain.txt`
- `/workspaces/job/career/profile/profile.yaml`
- `/workspaces/job/career/search/state/jobs.jsonl`
- `/workspaces/job/career/search/state/applications.jsonl`
- `/workspaces/job/career/state/memory_review.jsonl`

Treat `cv_plain.txt` as the canonical candidate profile, `profile.yaml` as the canonical confirmed preferences/memory store, and Markdown batches as the human-facing source that the ledger rebuild script parses into canonical JSONL state.
When the user confirms a missing preference during search, persist it with `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py` instead of hand-editing the profile.
