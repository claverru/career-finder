# Resume Import

Use `scripts/import_resume.py` when onboarding from `TXT`, `MD`, `DOCX`, `PDF`, or an image file.

It writes:

- `career/profile/imported_resume.txt`
- `career/state/import_review.jsonl` with extraction method, confidence, detected contacts, and detected sections

Rules:

- imported text is staging input, not canonical fact
- OCR results are low-confidence and need review
- when normalizing into `cv_plain.txt`, omit sections that are absent
