# Job Search Eval Cases

## Case 1: Aggregator link rejected

- Input: a role discovered through Remotive with no verified direct apply URL.
- Expected: the role can be noted as discovery-only, but `final_company_apply_url` stays null and the role is not treated as fully verified.

## Case 2: Unconfirmed company dislike

- Input: a historical note saying "not interested in X" with no explicit confirmation in `profile.yaml`.
- Expected: the note enters or remains in `memory_review.jsonl`, `jobs.jsonl` keeps the raw `user_note`, and `review_reason` explains why the note still needs confirmation.

## Case 3: Spain hiring hard filter

- Input: a remote role with no explicit Spain hiring signal.
- Expected: the role is rejected or kept pending verification, never treated as a clean match.

## Case 4: Salary labeling

- Input: one role with explicit company salary and one role with inferred market salary.
- Expected: the explicit role is labeled `Explicit`; the inferred role is labeled `Inferred` with evidence and confidence.

## Case 5: Duplicate prevention

- Input: a role already present in `jobs.jsonl`.
- Expected: the new run does not create a second canonical job entry with the same `dedupe_key`.

## Executable fixtures

- Run `python /workspaces/job/career/evals/run_v2_evals.py` to cover search-brief generation, query planning, source normalization, verification evidence extraction, and search-run reuse.
