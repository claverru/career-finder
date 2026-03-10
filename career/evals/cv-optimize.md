# CV Optimize Eval Cases

## Case 1: No invented facts

- Input: ask for a stronger Staff ML CV using only the canonical candidate profile text.
- Expected: output uses only facts, dates, technologies, and achievements present in `cv_plain.txt`.

## Case 2: Tailoring to a target role

- Input: tailor the CV for a Senior Applied ML Engineer role focused on production NLP.
- Expected: summary and emphasis change, but core facts remain unchanged and grounded in the evidence already present in `cv_plain.txt`.

## Case 3: Missing preference

- Input: ask to optimize the CV for a role that requires a relocation preference not present in `profile.yaml`.
- Expected: the agent asks once instead of assuming the candidate is open to relocation.

## Case 4: Artifact sync

- Input: update a fact in `cv_plain.txt` and run artifact sync.
- Expected: `render/main.tex` reflects the updated source of truth.

## Case 5: Confirmed preference persistence

- Input: the user confirms a missing preference such as salary expectation or a blocked company.
- Expected: `set_preference.py` updates the canonical YAML at an existing confirmed-preference or confirmed-memory path without duplicating candidate facts into `profile.yaml`.
