# Career Agent Repo

This repository packages a Codex-based career agent for two main workflows:

- resume review and tailoring through the repo-local skill `cv-optimize`
- job discovery, validation, and tracking through the repo-local skill `job-search-runbook`

## Quick Start

1. Create your local canonical files from the shared examples:

```bash
cp career/profile/cv_plain.example.txt career/profile/cv_plain.txt
cp career/profile/profile.example.yaml career/profile/profile.yaml
```

2. Replace the placeholder candidate facts in `career/profile/cv_plain.txt`.

3. Leave high-impact preferences in `career/profile/profile.yaml` as `null` or empty if you want the agent to ask for them on the first relevant task.

4. Invoke the agent with one of these workflows:

- `Use $cv-optimize to review and tailor my resume`
- `Use $job-search-runbook to search for jobs and update my search state`

## Shared vs Local Files

Shared files that should be pushed:

- `.agents/skills/`
- `career/profile/cv_plain.example.txt`
- `career/profile/profile.example.yaml`
- `career/search/policy/workflow.md`
- `career/search/batches/README.md`
- `career/evals/`

Local files that should stay private and are ignored by `.gitignore`:

- `career/profile/cv_plain.txt`
- `career/profile/profile.yaml`
- `career/profile/render/main.tex`
- `career/profile/render/main.pdf`
- `career/search/batches/[0-9]*.md`
- `career/search/state/*.jsonl`
- `career/state/*.jsonl`

## Preference Behavior

The agent is designed to ask once and persist the answer when a task depends on a missing high-impact preference such as:

- remote or onsite constraints
- hiring geography restrictions
- contract preferences
- compensation expectations
- company blocks or strong dislikes

It does not run a mandatory first-run questionnaire. Preference collection is lazy and task-driven by design.

## Publishing Note

`.gitignore` prevents new local profile and search-state files from being added by default. If you already tracked personal files in a git repository before adding `.gitignore`, remove them from the index before publishing.
