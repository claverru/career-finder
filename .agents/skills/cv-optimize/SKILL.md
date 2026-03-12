---
name: cv-optimize
description: Analyze, improve, and tailor the candidate resume from the canonical profile text, reusable evidence, and confirmed preferences. Use when Codex needs to review the resume, identify missing evidence, update candidate facts, generate a targeted resume for a role, or sync the LaTeX artifact without inventing claims.
---

# Cv Optimize

Use this skill for resume import, review, tailoring, fact updates, and LaTeX sync.

## Workflow

1. Read `/workspaces/job/career/AGENTS.md`.
2. If the user provides a resume file or `cv_plain.txt` is missing, run `scripts/import_resume.py` first. Treat OCR output as staging input that needs review.
3. Edit candidate narrative only in `career/profile/cv_plain.txt`. Use `career/profile/profile.yaml` only for confirmed preferences and memory.
4. Tailor by reordering and rephrasing evidence that already exists. If evidence is missing, call out the gap instead of fabricating fit.
5. Persist confirmed long-lived preferences or memory with `scripts/set_preference.py`.
6. After changing `cv_plain.txt`, run `scripts/render_artifacts.py`.

## Read only if needed

- `references/profile-schema.md` for file roles and seeds
- `references/resume-import.md` for importer behavior and confidence rules

## Validation

- `python scripts/render_artifacts.py`
- `python scripts/import_resume.py /path/to/resume.pdf`
