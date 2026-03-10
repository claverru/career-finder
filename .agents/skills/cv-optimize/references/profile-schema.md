# Profile Schema

Canonical profile model:

- Candidate facts and reusable evidence: `/workspaces/job/career/profile/cv_plain.txt`
- Confirmed preferences and memory: `/workspaces/job/career/profile/profile.yaml`
- Example seed files for a clean clone: `/workspaces/job/career/profile/cv_plain.example.txt` and `/workspaces/job/career/profile/profile.example.yaml`

Read these sources as needed:

- `cv_plain.txt`: contact info, positioning, skills, experience, education, projects, and evidence bank.
- `preferences.confirmed`: confirmed search and CV preferences.
- `memory.confirmed`: confirmed long-lived memory by company, domain, and location.

Generated artifacts:

- LaTeX artifact: `/workspaces/job/career/profile/render/main.tex`
- Confirmed preference writer: `/workspaces/job/.agents/skills/cv-optimize/scripts/set_preference.py`

Never duplicate the full CV narrative into `profile.yaml`; keep candidate facts in `cv_plain.txt` and structured preferences in YAML.
