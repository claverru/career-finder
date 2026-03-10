#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


CAREER_ROOT = Path(__file__).resolve().parents[4] / "career"
BATCHES_DIR = CAREER_ROOT / "search" / "batches"
JOBS_PATH = CAREER_ROOT / "search" / "state" / "jobs.jsonl"
APPLICATIONS_PATH = CAREER_ROOT / "search" / "state" / "applications.jsonl"
MEMORY_REVIEW_PATH = CAREER_ROOT / "state" / "memory_review.jsonl"

ROLE_RE = re.compile(r"^(?P<label>[A-Z]?\d+)\)\s+(?P<body>.+)$")
FIELD_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
NOTE_RE = re.compile(r"^->\s*(.*)$")

FIELD_MAP = {
    "verified status": "verification_state",
    "remote policy quote": "remote_policy_quote",
    "contract type quote": "contract_type_signal",
    "contract type signal": "contract_type_signal",
    "spain hiring quote": "spain_hiring_quote",
    "deep learning scope quote": "deep_learning_scope_quote",
    "deep learning/modeling quote": "deep_learning_scope_quote",
    "deployment scope quote": "deployment_scope_quote",
    "salary band": "salary_band",
    "salary basis": "salary_basis",
    "salary confidence": "salary_confidence",
    "salary evidence": "salary_evidence",
    "consulting risk": "consulting_risk",
    "direct company apply link": "final_company_apply_url",
    "link": "discovery_url",
    "posted": "posted_date",
}

AGGREGATOR_HOSTS = {
    "remotive.com",
    "www.remotive.com",
    "jobs.glynncapital.com",
}

COMPANY_PREFERENCE_NOTE_TOKENS = (
    "not interested",
    "not convinced",
    "looks weak",
    "looks doomed",
)

LOCATION_PREFERENCE_NOTE_TOKENS = (
    "not in madrid",
    "barcelona-tagged",
    "barcelona",
    "palma",
    "madrid",
    "location ",
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value).strip().lower()


def slugify(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def split_company_role(body: str) -> tuple[str, str]:
    if " — " in body:
        company, role = body.split(" — ", 1)
        return company.strip(), role.strip()
    if " - " in body:
        company, role = body.split(" - ", 1)
        return company.strip(), role.strip()
    return body.strip(), ""


def parse_batch(path: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None
    raw_text = path.read_text(encoding="utf-8")

    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()
        role_match = ROLE_RE.match(line)
        if role_match:
            if current:
                entries.append(current)
            company, role = split_company_role(role_match.group("body"))
            current = {
                "batch_id": path.stem,
                "source_date": path.stem.split("_", 1)[0],
                "company": company,
                "role": role,
                "source_file": str(path.relative_to(CAREER_ROOT)),
                "fields": {},
                "user_note": None,
            }
            continue

        if not current:
            continue

        field_match = FIELD_RE.match(line)
        if field_match:
            raw_key = normalize_text(field_match.group(1))
            field_name = FIELD_MAP.get(raw_key)
            if field_name:
                current["fields"][field_name] = field_match.group(2).strip()
            continue

        note_match = NOTE_RE.match(line)
        if note_match:
            current["user_note"] = note_match.group(1).strip()

    if current:
        entries.append(current)
    return entries


def aggregator_url(url: Optional[str]) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return host in AGGREGATOR_HOSTS


def infer_status(note: Optional[str], record: Dict[str, object]) -> str:
    if not note:
        if record.get("final_company_apply_url"):
            return "new"
        return "discovered"

    normalized = normalize_text(note)
    if any(token in normalized for token in ["applied", "applied already"]):
        return "applied"
    if "pending" in normalized:
        return "pending"
    if any(
        token in normalized
        for token in [
            "not interested",
            "not convinced",
            "looks weak",
            "looks doomed",
        ]
    ):
        return "discarded"
    if any(
        token in normalized
        for token in [
            "no longer listed",
            "not open in spain",
            "no open roles found",
            "not in madrid",
            "hybrid",
            "barcelona-tagged",
            "location ",
        ]
    ):
        return "discarded"
    return "new"


def make_memory_review(record: Dict[str, object]) -> Optional[Dict[str, object]]:
    note = record.get("user_note")
    if not note:
        return None

    normalized = normalize_text(str(note))
    company = str(record["company"])
    role = str(record["role"])

    if any(token in normalized for token in COMPANY_PREFERENCE_NOTE_TOKENS):
        return {
            "candidate_type": "company_preference",
            "scope": "company",
            "value": company,
            "source_note": note,
            "review_reason": "Historical note may imply a stable company preference. Confirm it before persisting or using it as a hard filter.",
            "company": company,
            "role": role,
            "source_batch_id": record["batch_id"],
            "status": "pending_review",
        }

    if any(token in normalized for token in LOCATION_PREFERENCE_NOTE_TOKENS):
        return {
            "candidate_type": "location_preference",
            "scope": "search.geography",
            "value": note,
            "source_note": note,
            "review_reason": "Historical note may imply a location preference or relocation constraint. Confirm it before using it as a hard filter.",
            "company": company,
            "role": role,
            "source_batch_id": record["batch_id"],
            "status": "pending_review",
        }

    return None


def merge_record(existing: Dict[str, object], new_record: Dict[str, object]) -> Dict[str, object]:
    merged = dict(existing)
    for key, value in new_record.items():
        if key in {"source_batches", "notes_history"}:
            continue
        if value not in (None, "", []):
            merged[key] = value

    merged.setdefault("source_batches", [])
    merged.setdefault("notes_history", [])
    if new_record["batch_id"] not in merged["source_batches"]:
        merged["source_batches"].append(new_record["batch_id"])
    if new_record.get("user_note"):
        merged["notes_history"].append(
            {
                "batch_id": new_record["batch_id"],
                "note": new_record["user_note"],
            }
        )
    return merged


def job_record_from_entry(entry: Dict[str, object]) -> Dict[str, object]:
    fields = dict(entry["fields"])
    discovery_url = fields.get("discovery_url")
    final_url = fields.get("final_company_apply_url")
    review_candidate = make_memory_review(entry)

    if aggregator_url(final_url):
        discovery_url = final_url
        final_url = None
    elif not final_url and aggregator_url(discovery_url):
        discovery_url = discovery_url

    dedupe_key = f"{slugify(str(entry['company']))}__{slugify(str(entry['role']))}"
    user_note = entry.get("user_note")
    record = {
        "dedupe_key": dedupe_key,
        "company": entry["company"],
        "role": entry["role"],
        "batch_id": entry["batch_id"],
        "source_batches": [entry["batch_id"]],
        "source_date": entry["source_date"],
        "posted_date": fields.get("posted_date"),
        "status": None,
        "discovery_url": discovery_url,
        "final_company_apply_url": final_url,
        "verification_state": fields.get("verification_state"),
        "remote_policy_quote": fields.get("remote_policy_quote"),
        "contract_type_signal": fields.get("contract_type_signal"),
        "spain_hiring_quote": fields.get("spain_hiring_quote"),
        "deep_learning_scope_quote": fields.get("deep_learning_scope_quote"),
        "deployment_scope_quote": fields.get("deployment_scope_quote"),
        "salary_band": fields.get("salary_band"),
        "salary_basis": fields.get("salary_basis"),
        "salary_confidence": fields.get("salary_confidence"),
        "salary_evidence": fields.get("salary_evidence"),
        "consulting_risk": fields.get("consulting_risk"),
        "user_note": user_note,
        "review_required": review_candidate is not None,
        "review_reason": review_candidate["review_reason"] if review_candidate else None,
        "notes_history": [],
        "source_file": entry["source_file"],
    }
    record["status"] = infer_status(user_note, record)
    if user_note:
        record["notes_history"].append({"batch_id": entry["batch_id"], "note": user_note})
    return record


def application_event_from_record(record: Dict[str, object]) -> Optional[Dict[str, object]]:
    if record["status"] in {"new", "discovered"} and not record.get("user_note"):
        return None
    return {
        "dedupe_key": record["dedupe_key"],
        "company": record["company"],
        "role": record["role"],
        "status": record["status"],
        "source_batch_id": record["batch_id"],
        "recorded_on": record["source_date"],
        "note": record.get("user_note"),
    }


def write_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def main() -> None:
    jobs_by_key: Dict[str, Dict[str, object]] = {}
    application_events: List[Dict[str, object]] = []
    review_candidates: List[Dict[str, object]] = []

    for path in sorted(BATCHES_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        entries = parse_batch(path)
        for entry in entries:
            record = job_record_from_entry(entry)
            existing = jobs_by_key.get(record["dedupe_key"])
            jobs_by_key[record["dedupe_key"]] = merge_record(existing, record) if existing else record

            application_event = application_event_from_record(record)
            if application_event:
                application_events.append(application_event)

            review_candidate = make_memory_review(entry)
            if review_candidate:
                review_candidates.append(review_candidate)

    jobs = [jobs_by_key[key] for key in sorted(jobs_by_key)]
    application_events.sort(key=lambda row: (row["recorded_on"], row["company"], row["role"]))
    review_candidates.sort(key=lambda row: (row["source_batch_id"], row["company"], row["role"], row["source_note"]))

    write_jsonl(JOBS_PATH, jobs)
    write_jsonl(APPLICATIONS_PATH, application_events)
    write_jsonl(MEMORY_REVIEW_PATH, review_candidates)


if __name__ == "__main__":
    main()
