# Career Agent Repo

This repository packages a Codex-based career agent with two repo-local skills:

- `cv-optimize` for resume import, review, tailoring, and artifact sync
- `job-search-runbook` for staged job discovery, verification, and tracking

## Quick Start

1. Seed local files from the shared examples:

```bash
cp career/profile/cv_plain.example.txt career/profile/cv_plain.txt
cp career/profile/profile.example.yaml career/profile/profile.yaml
```

2. Onboard in one of two ways:

- import an existing resume by asking Codex to use `$cv-optimize` on a local `PDF`, `DOCX`, `TXT`, `MD`, or image resume
- or replace the placeholder candidate facts in `career/profile/cv_plain.txt` manually

3. Leave high-impact preferences in `career/profile/profile.yaml` as `null` or empty if you want the agent to ask when they first matter.

4. Typical prompts:

- `Use $cv-optimize to import this resume and build my canonical profile`
- `Use $cv-optimize to review and tailor my resume`
- `Use $job-search-runbook to prepare my search brief and run the staged search pipeline`

## Shared vs Local Files

Shared files that should be pushed:

- `.agents/skills/`
- `career/profile/cv_plain.example.txt`
- `career/profile/profile.example.yaml`
- `career/search/policy/workflow.md`
- `career/search/policy/source_catalog.example.yaml`
- `career/search/batches/README.md`
- `career/evals/`

Local files that should stay private and are ignored by `.gitignore`:

- `career/profile/cv_plain.txt`
- `career/profile/imported_resume.txt`
- `career/profile/profile.yaml`
- `career/profile/render/main.tex`
- `career/profile/render/main.pdf`
- `career/search/policy/source_catalog.yaml`
- `career/search/batches/[0-9]*.md`
- `career/state/search/*.jsonl`
- `career/state/search/compact_jobs.md`
- `career/state/prospecting/*.jsonl`
- `career/state/*.jsonl`

## Preference Behavior

The agent asks once and persists the answer when a task depends on a missing high-impact preference such as:

- remote or onsite constraints
- hiring geography restrictions
- contract preferences
- compensation expectations
- company blocks or strong dislikes

It does not run a mandatory onboarding questionnaire. Preference collection is lazy and task-driven.

## Search Model

Search is staged:

1. build the search brief
2. derive the query plan and source priority
3. discover jobs from official or public sources
4. verify and rank results before drafting a batch

Supported adapters cover Greenhouse, Lever, public Ashby boards, official careers pages, and LinkedIn public discovery.

## Publishing Note

`.gitignore` prevents new local profile and career-state files from being added by default. If you already tracked personal files in a git repository before adding `.gitignore`, remove them from the index before publishing.
