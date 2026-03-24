# Prospecting Batches

This directory contains the active human-readable company-prospecting batches in Markdown format.

- Each file is named `{YYYYMMDD}_{n}.md`.
- Use these files as user-facing reports.
- Use `/workspaces/job/career/state/prospecting/prospects.jsonl`, `/workspaces/job/career/state/prospecting/contacts.jsonl`, and `/workspaces/job/career/state/prospecting/runs.jsonl` as the canonical automation state.
- Rebuild the structured ledgers from these Markdown batches with `.agents/skills/company-prospecting-runbook/scripts/sync_prospect_state.py`.
