---
name: cv-optimize
description: Analyze, improve, and tailor the candidate resume from the canonical profile text, reusable evidence, and confirmed preferences. Use when Codex needs to review the resume, identify missing evidence, update candidate facts, generate a targeted resume for a role, or sync the LaTeX artifact without inventing claims.
---

# Cv Optimize

## Workflow

1. Read `/workspaces/job/career/profile/cv_plain.txt` as the canonical local source for candidate facts, resume content, and reusable evidence.
2. Read `/workspaces/job/career/profile/profile.yaml` for confirmed preferences, confirmed memory, and resume guardrails.
3. If those local files are missing in a clean clone, seed them from `/workspaces/job/career/profile/cv_plain.example.txt` and `/workspaces/job/career/profile/profile.example.yaml`.
4. When tailoring for a role, read the job description and select only evidence that exists in `cv_plain.txt`.
5. If the task depends on a missing high-impact preference, ask once and persist the answer in `profile.yaml`. Use `scripts/set_preference.py` for confirmed preferences or confirmed memory so the update is repeatable.
6. After changing canonical resume content in `cv_plain.txt`, run `scripts/render_artifacts.py` to regenerate `profile/render/main.tex`.

## Guardrails

- Do not invent achievements, dates, technologies, titles, salary expectations, or preferences.
- Prefer stronger phrasing only when it is supported by the canonical evidence.
- Keep leadership, production ownership, and deep-learning breadth visible because they are confirmed strengths.
- When a role asks for unavailable evidence, surface the gap instead of fabricating fit.

## Repo resources

- Schema reference: `references/profile-schema.md`
- CV workflow reference: `references/cv-workflow.md`
- Confirmed preference writer: `scripts/set_preference.py`
- Artifact renderer: `scripts/render_artifacts.py`

## Typical tasks

- Improve the generic CV while preserving factual fidelity.
- Tailor the resume for a job description.
- Convert a newly confirmed preference into canonical structured profile data.
- Update `cv_plain.txt` when candidate facts change, then regenerate the LaTeX artifact.

## Validation

- Run `python scripts/render_artifacts.py` after changing `cv_plain.txt`.
- Run `python scripts/set_preference.py preferences.confirmed.search.remote_policy.mode remote_only --dry-run` to preview a preference update without editing YAML manually.
- Review the generated LaTeX artifact for formatting regressions.
