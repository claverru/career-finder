#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import sys


SCRIPT_DIR = Path(__file__).resolve().parent
COMMON_DIR = SCRIPT_DIR.parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

import career_shared


CAREER_ROOT = career_shared.CAREER_ROOT
BATCHES_DIR = CAREER_ROOT / "search" / "batches"
career_shared.ensure_state_layout()
JOBS_PATH = career_shared.SEARCH_JOBS_PATH
APPLICATIONS_PATH = career_shared.SEARCH_APPLICATIONS_PATH
MEMORY_REVIEW_PATH = career_shared.MEMORY_REVIEW_PATH
COMPACT_JOBS_PATH = career_shared.SEARCH_COMPACT_JOBS_PATH
PROFILE_PATH = career_shared.DEFAULT_PROFILE_PATH

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
    "source kind": "source_kind",
    "source record id": "source_record_id",
    "evidence urls": "evidence_urls",
    "first seen at": "first_seen_at",
    "last seen at": "last_seen_at",
    "search run id": "search_run_id",
    "verification confidence": "verification_confidence",
    "user status": "user_status",
    "candidate status": "user_status",
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
ALLOWED_JOB_STATUSES = {
    "discovered",
    "new",
    "applied",
    "interview",
    "pending",
    "discarded",
}
STATUS_SORT_ORDER = {
    "interview": 0,
    "pending": 1,
    "applied": 2,
    "new": 3,
    "discovered": 4,
    "discarded": 5,
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value).strip().lower()


def slugify(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_status_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = normalize_text(value).replace(" ", "_")
    if normalized in ALLOWED_JOB_STATUSES:
        return normalized
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge search batches into persistent search state and regenerate the compact process view.",
    )
    parser.add_argument(
        "--compact-only",
        action="store_true",
        help="Only regenerate the compact state document from the current persistent jobs ledger.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def canonicalize_job_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if not parsed.netloc:
        return None
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"{scheme}://{host}{path}"


def compute_internal_job_id(record: Dict[str, object]) -> str:
    existing = record.get("internal_job_id")
    if isinstance(existing, str) and existing.strip():
        return existing

    canonical_url = canonicalize_job_url(
        str(record.get("final_company_apply_url") or record.get("discovery_url") or "").strip() or None
    )
    if canonical_url:
        seed = f"url:{canonical_url}"
    else:
        dedupe_key = str(record.get("dedupe_key") or "").strip()
        if not dedupe_key:
            company = slugify(str(record.get("company") or ""))
            role = slugify(str(record.get("role") or ""))
            dedupe_key = f"{company}__{role}".strip("_")
        seed = f"dedupe:{dedupe_key}"

    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"job_{digest}"


def normalize_existing_job(record: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(record)
    normalized.setdefault("source_batches", [])
    normalized.setdefault("notes_history", [])
    normalized["internal_job_id"] = compute_internal_job_id(normalized)
    return normalized


def normalize_application_event(record: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(record)
    if "internal_job_id" not in normalized:
        normalized["internal_job_id"] = None
    return normalized


def application_event_key(record: Dict[str, object]) -> tuple[str, str]:
    return (
        str(record.get("dedupe_key") or ""),
        str(record.get("source_batch_id") or ""),
    )


def review_candidate_key(record: Dict[str, object]) -> tuple[str, str, str, str, str]:
    return (
        str(record.get("candidate_type") or ""),
        str(record.get("company") or ""),
        str(record.get("role") or ""),
        str(record.get("source_batch_id") or ""),
        str(record.get("source_note") or ""),
    )


def confirmed_company_names(profile: Dict[str, object]) -> set[str]:
    names: set[str] = set()
    paths = (
        "preferences.confirmed.search.company_preferences.preferred",
        "preferences.confirmed.search.company_preferences.blocked_confirmed",
        "memory.confirmed.companies.preferred",
        "memory.confirmed.companies.blocked",
    )
    for path in paths:
        values = career_shared.get_dotted(profile, path) or []
        for value in values:
            normalized = normalize_text(str(value))
            if normalized:
                names.add(normalized)
    return names


def review_candidate_confirmed(
    record: Dict[str, object],
    *,
    confirmed_companies: set[str],
) -> bool:
    if str(record.get("candidate_type") or "") != "company_preference":
        return False
    company = normalize_text(str(record.get("company") or record.get("value") or ""))
    return bool(company) and company in confirmed_companies


def compact_row_sort_key(record: Dict[str, object]) -> tuple[int, str, str]:
    status = str(record.get("status") or "")
    return (
        STATUS_SORT_ORDER.get(status, len(STATUS_SORT_ORDER)),
        normalize_text(str(record.get("company") or "")),
        normalize_text(str(record.get("role") or "")),
    )


def escape_markdown_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_compact_jobs(jobs: List[Dict[str, object]]) -> str:
    lines = [
        "# Compact Search State",
        "",
        f"Updated at: {datetime.now(timezone.utc).date().isoformat()}",
        f"Rows: {len(jobs)}",
        "",
        "| Internal Job ID | Title | Company | Salary | Status |",
        "| --- | --- | --- | --- | --- |",
    ]

    for row in sorted(jobs, key=compact_row_sort_key):
        salary = row.get("salary_band") or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{escape_markdown_cell(row.get('internal_job_id'))}`",
                    escape_markdown_cell(row.get("role")),
                    escape_markdown_cell(row.get("company")),
                    escape_markdown_cell(salary),
                    f"`{escape_markdown_cell(row.get('status'))}`",
                ]
            )
            + " |"
        )

    lines.append("")
    return "\n".join(lines)


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
                raw_value = field_match.group(2).strip()
                if field_name == "evidence_urls":
                    current["fields"][field_name] = [item.strip() for item in raw_value.split(";") if item.strip()]
                else:
                    current["fields"][field_name] = raw_value
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
    explicit_status = normalize_status_value(record.get("user_status"))
    if explicit_status:
        return explicit_status

    if not note:
        if record.get("final_company_apply_url"):
            return "new"
        return "discovered"

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
        if key == "internal_job_id" and existing.get("internal_job_id"):
            continue
        if (
            key == "status"
            and value == "new"
            and not new_record.get("user_note")
            and existing.get("status") in {"applied", "interview", "pending", "discarded"}
        ):
            continue
        if value not in (None, "", []):
            merged[key] = value

    merged.setdefault("source_batches", [])
    merged.setdefault("notes_history", [])
    merged["internal_job_id"] = compute_internal_job_id(merged)
    if new_record["batch_id"] not in merged["source_batches"]:
        merged["source_batches"].append(new_record["batch_id"])
    if new_record.get("user_note"):
        note_entry = {
            "batch_id": new_record["batch_id"],
            "note": new_record["user_note"],
        }
        if note_entry not in merged["notes_history"]:
            merged["notes_history"].append(note_entry)
    return merged


def job_record_from_entry(entry: Dict[str, object]) -> Dict[str, object]:
    fields = dict(entry["fields"])
    discovery_url = fields.get("discovery_url")
    final_url = fields.get("final_company_apply_url")
    review_candidate = make_memory_review(entry)
    explicit_status = normalize_status_value(fields.get("user_status"))

    if aggregator_url(final_url):
        discovery_url = final_url
        final_url = None
    elif not final_url and aggregator_url(discovery_url):
        discovery_url = discovery_url

    dedupe_key = f"{slugify(str(entry['company']))}__{slugify(str(entry['role']))}"
    user_note = entry.get("user_note")
    record = {
        "internal_job_id": None,
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
        "source_kind": fields.get("source_kind"),
        "source_record_id": fields.get("source_record_id"),
        "evidence_urls": fields.get("evidence_urls") or [],
        "first_seen_at": fields.get("first_seen_at") or entry["source_date"],
        "last_seen_at": fields.get("last_seen_at") or entry["source_date"],
        "search_run_id": fields.get("search_run_id"),
        "verification_confidence": fields.get("verification_confidence"),
        "notes_history": [],
        "source_file": entry["source_file"],
    }
    record["internal_job_id"] = compute_internal_job_id(record)
    record["status"] = infer_status(user_note, {"final_company_apply_url": final_url, "user_status": explicit_status})
    if user_note:
        record["notes_history"].append({"batch_id": entry["batch_id"], "note": user_note})
    return record


def application_event_from_record(record: Dict[str, object]) -> Optional[Dict[str, object]]:
    if record["status"] in {"new", "discovered"} and not record.get("user_note"):
        return None
    return {
        "internal_job_id": record.get("internal_job_id"),
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


def write_compact_jobs(jobs: List[Dict[str, object]]) -> None:
    COMPACT_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPACT_JOBS_PATH.write_text(render_compact_jobs(jobs), encoding="utf-8")


def sync(compact_only: bool = False) -> Dict[str, int]:
    profile = career_shared.read_yaml(PROFILE_PATH)
    confirmed_companies = confirmed_company_names(profile)
    jobs_by_key: Dict[str, Dict[str, object]] = {
        str(row["dedupe_key"]): normalize_existing_job(row)
        for row in load_jsonl(JOBS_PATH)
        if row.get("dedupe_key")
    }
    application_events_by_key = {
        application_event_key(row): normalize_application_event(row)
        for row in load_jsonl(APPLICATIONS_PATH)
    }
    review_candidates_by_key = {
        review_candidate_key(row): dict(row)
        for row in load_jsonl(MEMORY_REVIEW_PATH)
        if not review_candidate_confirmed(dict(row), confirmed_companies=confirmed_companies)
    }

    batches_scanned = 0
    if not compact_only:
        for path in sorted(BATCHES_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            batches_scanned += 1
            entries = parse_batch(path)
            for entry in entries:
                record = job_record_from_entry(entry)
                existing = jobs_by_key.get(record["dedupe_key"])
                merged = merge_record(existing, record) if existing else record
                merged["internal_job_id"] = compute_internal_job_id(merged)
                jobs_by_key[record["dedupe_key"]] = merged

                application_event = application_event_from_record(record)
                if application_event:
                    application_event["internal_job_id"] = merged["internal_job_id"]
                    application_events_by_key[application_event_key(application_event)] = application_event

                review_candidate = make_memory_review(entry)
                if review_candidate and not review_candidate_confirmed(
                    review_candidate,
                    confirmed_companies=confirmed_companies,
                ):
                    review_candidates_by_key[review_candidate_key(review_candidate)] = review_candidate

    jobs = sorted(
        (normalize_existing_job(row) for row in jobs_by_key.values()),
        key=lambda row: normalize_text(str(row.get("dedupe_key") or "")),
    )
    internal_id_by_dedupe = {
        str(row.get("dedupe_key") or ""): str(row.get("internal_job_id") or "")
        for row in jobs
        if row.get("dedupe_key") and row.get("internal_job_id")
    }
    application_events = sorted(
        (
            {
                **row,
                "internal_job_id": row.get("internal_job_id")
                or internal_id_by_dedupe.get(str(row.get("dedupe_key") or ""), None),
            }
            for row in application_events_by_key.values()
        ),
        key=lambda row: (str(row.get("recorded_on") or ""), str(row.get("company") or ""), str(row.get("role") or "")),
    )
    review_candidates = sorted(
        review_candidates_by_key.values(),
        key=lambda row: (
            str(row.get("source_batch_id") or ""),
            str(row.get("company") or ""),
            str(row.get("role") or ""),
            str(row.get("source_note") or ""),
        ),
    )

    write_jsonl(JOBS_PATH, jobs)
    write_jsonl(APPLICATIONS_PATH, application_events)
    write_jsonl(MEMORY_REVIEW_PATH, review_candidates)
    write_compact_jobs(jobs)

    return {
        "jobs": len(jobs),
        "applications": len(application_events),
        "review_candidates": len(review_candidates),
        "batches_scanned": batches_scanned,
    }


def main() -> None:
    args = parse_args()
    sync(compact_only=args.compact_only)


if __name__ == "__main__":
    main()
