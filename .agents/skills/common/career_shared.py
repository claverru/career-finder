#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


CAREER_ROOT = Path(__file__).resolve().parents[3] / "career"
STATE_ROOT = CAREER_ROOT / "state"
SEARCH_STATE_DIR = STATE_ROOT / "search"
PROSPECTING_STATE_DIR = STATE_ROOT / "prospecting"
DEFAULT_PROFILE_PATH = CAREER_ROOT / "profile" / "profile.yaml"
DEFAULT_CV_PATH = CAREER_ROOT / "profile" / "cv_plain.txt"
MEMORY_REVIEW_PATH = STATE_ROOT / "memory_review.jsonl"
SEARCH_JOBS_PATH = SEARCH_STATE_DIR / "jobs.jsonl"
SEARCH_APPLICATIONS_PATH = SEARCH_STATE_DIR / "applications.jsonl"
SEARCH_RUNS_PATH = SEARCH_STATE_DIR / "runs.jsonl"
SEARCH_DISCOVERY_CANDIDATES_PATH = SEARCH_STATE_DIR / "discovery_candidates.jsonl"
SEARCH_RANKED_CANDIDATES_PATH = SEARCH_STATE_DIR / "ranked_candidates.jsonl"
SEARCH_COMPACT_JOBS_PATH = SEARCH_STATE_DIR / "compact_jobs.md"
PROSPECTS_PATH = PROSPECTING_STATE_DIR / "prospects.jsonl"
CONTACTS_PATH = PROSPECTING_STATE_DIR / "contacts.jsonl"
PROSPECT_RUNS_PATH = PROSPECTING_STATE_DIR / "runs.jsonl"
PROSPECT_DISCOVERY_CANDIDATES_PATH = PROSPECTING_STATE_DIR / "discovery_candidates.jsonl"
PROSPECT_RANKED_PROSPECTS_PATH = PROSPECTING_STATE_DIR / "ranked_prospects.jsonl"
PROSPECT_RESOLVED_CONTACTS_PATH = PROSPECTING_STATE_DIR / "resolved_contacts.jsonl"
SECTION_HEADERS = {
    "HEADLINE",
    "SUMMARY",
    "CAREER FOCUS",
    "SKILLS",
    "EXPERIENCE",
    "EDUCATION",
    "PROJECTS",
    "EVIDENCE BANK",
}
LEGACY_STATE_MOVES = {
    CAREER_ROOT / "search" / "state" / "jobs.jsonl": SEARCH_JOBS_PATH,
    CAREER_ROOT / "search" / "state" / "applications.jsonl": SEARCH_APPLICATIONS_PATH,
    CAREER_ROOT / "search" / "state" / "search_runs.jsonl": SEARCH_RUNS_PATH,
    CAREER_ROOT / "search" / "state" / "discovery_candidates.jsonl": SEARCH_DISCOVERY_CANDIDATES_PATH,
    CAREER_ROOT / "search" / "state" / "ranked_candidates.jsonl": SEARCH_RANKED_CANDIDATES_PATH,
    CAREER_ROOT / "search" / "state" / "compact_jobs.md": SEARCH_COMPACT_JOBS_PATH,
    CAREER_ROOT / "prospecting" / "state" / "prospects.jsonl": PROSPECTS_PATH,
    CAREER_ROOT / "prospecting" / "state" / "contacts.jsonl": CONTACTS_PATH,
    CAREER_ROOT / "prospecting" / "state" / "prospecting_runs.jsonl": PROSPECT_RUNS_PATH,
    CAREER_ROOT / "prospecting" / "state" / "discovery_candidates.jsonl": PROSPECT_DISCOVERY_CANDIDATES_PATH,
    CAREER_ROOT / "prospecting" / "state" / "ranked_prospects.jsonl": PROSPECT_RANKED_PROSPECTS_PATH,
    CAREER_ROOT / "prospecting" / "state" / "resolved_contacts.jsonl": PROSPECT_RESOLVED_CONTACTS_PATH,
}


def ensure_state_layout() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    SEARCH_STATE_DIR.mkdir(parents=True, exist_ok=True)
    PROSPECTING_STATE_DIR.mkdir(parents=True, exist_ok=True)
    for legacy_path, canonical_path in LEGACY_STATE_MOVES.items():
        if not legacy_path.exists() or canonical_path.exists():
            continue
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.replace(canonical_path)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value).strip().lower()


def slugify(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def stable_json_hash(payload: Any) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def get_dotted(mapping: dict[str, Any], dotted_path: str) -> Any:
    current: Any = mapping
    for segment in dotted_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def split_sections(cv_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in cv_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped in SECTION_HEADERS:
            current = stripped
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def parse_focus_roles(section_lines: list[str]) -> list[str]:
    for line in section_lines:
        if line.startswith("Target roles:"):
            return [item.strip() for item in line.removeprefix("Target roles:").split(",") if item.strip()]
    return []


def parse_focus_strengths(section_lines: list[str]) -> list[str]:
    for line in section_lines:
        if line.startswith("Strengths:"):
            return [item.strip() for item in line.removeprefix("Strengths:").split(",") if item.strip()]
    return []


def parse_skills(section_lines: list[str]) -> list[str]:
    skills: list[str] = []
    for line in section_lines:
        stripped = line.strip()
        if ":" not in stripped:
            continue
        _, values = stripped.split(":", 1)
        skills.extend(item.strip() for item in values.split(",") if item.strip())
    return skills


def parse_summary_points(section_lines: list[str]) -> list[str]:
    points: list[str] = []
    for line in section_lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            points.append(stripped[2:].strip())
    return points


def unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for value in values:
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def extract_candidate_context(cv_text: str) -> dict[str, Any]:
    sections = split_sections(cv_text)
    focus_lines = [line.strip() for line in sections.get("CAREER FOCUS", []) if line.strip()]
    return {
        "headline": next((line.strip() for line in sections.get("HEADLINE", []) if line.strip()), ""),
        "target_roles": parse_focus_roles(focus_lines),
        "strengths": parse_focus_strengths(focus_lines),
        "skills": parse_skills(sections.get("SKILLS", [])),
        "summary_points": parse_summary_points(sections.get("SUMMARY", [])),
    }


def dedupe_company_role_key(company: str, role_family: str) -> str:
    return f"{slugify(company)}__{slugify(role_family)}"
