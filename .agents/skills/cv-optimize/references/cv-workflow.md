# Resume Workflow

1. Load `cv_plain.txt` for candidate facts and reusable evidence.
2. Load `profile.yaml` for confirmed preferences, memory, and CV guardrails.
3. Identify the target outcome:
   - generic resume refresh,
   - tailored resume for a job description,
   - profile fact update,
   - evidence-gap review.
4. Rephrase and reorder content using only factual evidence already present.
5. If a requested claim is unsupported, call out the gap.
6. If the user confirms a preference or long-lived memory, persist it with `scripts/set_preference.py` instead of manually editing YAML.
7. After canonical resume-content changes, regenerate `render/main.tex` with `scripts/render_artifacts.py`.

When tailoring:

- Prioritize evidence that matches the target domain, stack, and seniority.
- Keep production ownership visible.
- Preserve chronology and titles unless the user explicitly requests a different presentation.
