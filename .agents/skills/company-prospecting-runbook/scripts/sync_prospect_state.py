#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
COMMON_DIR = SCRIPT_DIR.parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

import career_shared


CAREER_ROOT = career_shared.CAREER_ROOT
BATCHES_DIR = CAREER_ROOT / "prospecting" / "batches"
career_shared.ensure_state_layout()
PROSPECTS_PATH = career_shared.PROSPECTS_PATH
CONTACTS_PATH = career_shared.CONTACTS_PATH

ENTRY_RE = re.compile(r"^(?P<label>P?\d+)\)\s+(?P<body>.+)$")
FIELD_RE = re.compile(r"^-\s+([^:]+):\s*(.*)$")
NOTE_RE = re.compile(r"^->\s*(.*)$")

FIELD_MAP = {
    "prospect status": "status",
    "target role family": "target_role_family",
    "rationale": "rationale",
    "company potential score": "company_potential_score",
    "role plausibility score": "role_plausibility_score",
    "geography fit score": "geography_fit_score",
    "contactability score": "contactability_score",
    "evidence quality score": "evidence_quality_score",
    "total score": "total_score",
    "company potential quote": "company_potential_quote",
    "role plausibility quote": "role_plausibility_quote",
    "geography fit quote": "geography_fit_quote",
    "contactability quote": "contactability_quote",
    "selected contact type": "selected_contact_type",
    "selected contact": "selected_contact",
    "selected contact role": "selected_contact_role",
    "contact url or email": "selected_contact_url_or_email",
    "contact confidence": "contact_confidence",
    "selection reason": "selection_reason",
    "company url": "company_url",
    "discovery url": "discovery_url",
    "source kind": "source_kind",
    "source record id": "source_record_id",
    "evidence urls": "evidence_urls",
    "first seen at": "first_seen_at",
    "last seen at": "last_seen_at",
    "prospect run id": "prospect_run_id",
    "verification confidence": "verification_confidence",
}


def normalize_text(value: str) -> str:
    return career_shared.normalize_text(value)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return career_shared.load_jsonl(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    career_shared.write_jsonl(path, rows)


def parse_batch(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        entry_match = ENTRY_RE.match(line)
        if entry_match:
            if current:
                entries.append(current)
            current = {
                "batch_id": path.stem,
                "source_date": path.stem.split("_", 1)[0],
                "company": entry_match.group("body").strip(),
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


def parse_score(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def prospect_record_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    fields = dict(entry["fields"])
    role_family = fields.get("target_role_family") or "Generalist"
    dedupe_key = career_shared.dedupe_company_role_key(str(entry["company"]), str(role_family))
    return {
        "dedupe_key": dedupe_key,
        "company": entry["company"],
        "target_role_family": role_family,
        "status": fields.get("status") or "new",
        "rationale": fields.get("rationale"),
        "company_potential_score": parse_score(fields.get("company_potential_score")),
        "role_plausibility_score": parse_score(fields.get("role_plausibility_score")),
        "geography_fit_score": parse_score(fields.get("geography_fit_score")),
        "contactability_score": parse_score(fields.get("contactability_score")),
        "evidence_quality_score": parse_score(fields.get("evidence_quality_score")),
        "total_score": parse_score(fields.get("total_score")),
        "company_potential_quote": fields.get("company_potential_quote"),
        "role_plausibility_quote": fields.get("role_plausibility_quote"),
        "geography_fit_quote": fields.get("geography_fit_quote"),
        "contactability_quote": fields.get("contactability_quote"),
        "selected_contact_type": fields.get("selected_contact_type"),
        "selected_contact": fields.get("selected_contact"),
        "selected_contact_role": fields.get("selected_contact_role"),
        "selected_contact_url_or_email": fields.get("selected_contact_url_or_email"),
        "contact_confidence": fields.get("contact_confidence"),
        "company_url": fields.get("company_url"),
        "discovery_url": fields.get("discovery_url"),
        "source_kind": fields.get("source_kind"),
        "source_record_id": fields.get("source_record_id"),
        "evidence_urls": fields.get("evidence_urls") or [],
        "first_seen_at": fields.get("first_seen_at") or entry["source_date"],
        "last_seen_at": fields.get("last_seen_at") or entry["source_date"],
        "prospect_run_id": fields.get("prospect_run_id"),
        "verification_confidence": fields.get("verification_confidence"),
        "review_required": (fields.get("status") or "new") == "pending",
        "review_reason": entry.get("user_note"),
        "user_note": entry.get("user_note"),
        "batch_id": entry["batch_id"],
    }


def contact_record_from_prospect(prospect: dict[str, Any]) -> dict[str, Any] | None:
    if not prospect.get("selected_contact") or not prospect.get("selected_contact_url_or_email"):
        return None
    return {
        "contact_id": career_shared.stable_json_hash(
            [
                prospect["dedupe_key"],
                prospect.get("selected_contact"),
                prospect.get("selected_contact_url_or_email"),
            ]
        )[:12],
        "prospect_dedupe_key": prospect["dedupe_key"],
        "company": prospect["company"],
        "target_role_family": prospect["target_role_family"],
        "contact_type": prospect.get("selected_contact_type"),
        "name_or_channel": prospect.get("selected_contact"),
        "role": prospect.get("selected_contact_role"),
        "contact_url_or_email": prospect.get("selected_contact_url_or_email"),
        "confidence": prospect.get("contact_confidence"),
        "selection_reason": prospect.get("contactability_quote"),
        "evidence_urls": prospect.get("evidence_urls") or [],
        "prospect_run_id": prospect.get("prospect_run_id"),
        "selected": True,
    }


def merge_prospect(existing: dict[str, Any], new_record: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in new_record.items():
        if key in {"source_batches", "notes_history"}:
            continue
        if value not in (None, "", []):
            merged[key] = value
    merged.setdefault("source_batches", [])
    if new_record["batch_id"] not in merged["source_batches"]:
        merged["source_batches"].append(new_record["batch_id"])
    merged["evidence_urls"] = career_shared.unique_preserve_order(
        list(existing.get("evidence_urls") or []) + list(new_record.get("evidence_urls") or [])
    )
    if new_record.get("user_note"):
        merged.setdefault("notes_history", [])
        merged["notes_history"].append({"batch_id": new_record["batch_id"], "note": new_record["user_note"]})
    return merged


def sync() -> dict[str, int]:
    prospects_by_key: dict[str, dict[str, Any]] = {}
    contacts_by_key: dict[str, dict[str, Any]] = {}
    parsed_batches = 0

    for batch_path in sorted(BATCHES_DIR.glob("*.md")):
        if batch_path.name == "README.md":
            continue
        parsed_batches += 1
        for entry in parse_batch(batch_path):
            prospect = prospect_record_from_entry(entry)
            existing = prospects_by_key.get(prospect["dedupe_key"])
            if existing is None:
                prospects_by_key[prospect["dedupe_key"]] = prospect
            else:
                prospects_by_key[prospect["dedupe_key"]] = merge_prospect(existing, prospect)

            contact = contact_record_from_prospect(prospect)
            if contact is not None:
                contacts_by_key[contact["prospect_dedupe_key"]] = contact

    prospects = sorted(
        prospects_by_key.values(),
        key=lambda row: (row.get("status") != "new", -(row.get("total_score") or 0), row["company"], row["target_role_family"]),
    )
    contacts = [contacts_by_key[row["dedupe_key"]] for row in prospects if row["dedupe_key"] in contacts_by_key]

    write_jsonl(PROSPECTS_PATH, prospects)
    write_jsonl(CONTACTS_PATH, contacts)
    return {"prospects": len(prospects), "contacts": len(contacts), "batches": parsed_batches}


def main() -> None:
    print(json.dumps(sync(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
