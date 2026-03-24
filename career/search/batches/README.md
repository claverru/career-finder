# Search Batches

This directory contains the active human-readable search batches in Markdown format.

- Each file is named `{YYYYMMDD}_{n}.md`.
- Use these files as user-facing reports.
- Use `/workspaces/job/career/state/search/jobs.jsonl` and `/workspaces/job/career/state/search/applications.jsonl` as the canonical automation state.
- Rebuild the structured ledgers from these Markdown batches with `.agents/skills/job-search-runbook/scripts/sync_search_state.py`.
