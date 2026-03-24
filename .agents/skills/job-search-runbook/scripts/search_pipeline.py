#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

COMMON_DIR = Path(__file__).resolve().parents[2] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

import career_shared


CAREER_ROOT = career_shared.CAREER_ROOT
DEFAULT_PROFILE_PATH = career_shared.DEFAULT_PROFILE_PATH
DEFAULT_CV_PATH = career_shared.DEFAULT_CV_PATH
career_shared.ensure_state_layout()
DEFAULT_SEARCH_RUNS_PATH = career_shared.SEARCH_RUNS_PATH
DEFAULT_DISCOVERY_OUTPUT_PATH = career_shared.SEARCH_DISCOVERY_CANDIDATES_PATH
DEFAULT_RANKED_OUTPUT_PATH = career_shared.SEARCH_RANKED_CANDIDATES_PATH
DEFAULT_SOURCE_CATALOG_PATH = CAREER_ROOT / "search" / "policy" / "source_catalog.yaml"
DEFAULT_SOURCE_PRIORITY = [
    "greenhouse",
    "lever",
    "ashby_public",
    "company_html",
    "linkedin_public",
    "web_search",
]
AGGREGATOR_HOSTS = {
    "remotive.com",
    "www.remotive.com",
    "jobs.glynncapital.com",
}
BRIEF_FIELDS = [
    {
        "path": "preferences.confirmed.search.remote_policy.mode",
        "question": "What remote policy should the search use?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.geography.base",
        "question": "What is the base hiring location to optimize for?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.geography.hireable_from",
        "question": "From which countries or regions can the candidate be hired?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.contract.allowed",
        "question": "Which contract types are acceptable?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.role_scope.require_model_development",
        "question": "Should the search require hands-on model development work?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.role_scope.require_production_ownership",
        "question": "Should the search require production ownership for models or ML systems?",
        "blocking": True,
    },
    {
        "path": "preferences.confirmed.search.domains.preferred",
        "question": "Which domains should be preferred during ranking?",
        "blocking": False,
    },
    {
        "path": "preferences.confirmed.search.company_preferences.preferred",
        "question": "Are there any preferred companies to prioritize?",
        "blocking": False,
    },
    {
        "path": "preferences.confirmed.search.company_preferences.blocked_confirmed",
        "question": "Are there any companies that should be blocked for future searches?",
        "blocking": False,
    },
    {
        "path": "preferences.confirmed.search.compensation.salary_expectation_eur_base",
        "question": "Is there a compensation threshold that should influence ranking or filtering?",
        "blocking": False,
    },
]
SECTION_HEADERS = career_shared.SECTION_HEADERS
REMOTE_POSITIVE_PATTERNS = [
    "remote",
    "remote only",
    "remote-only",
    "remote basis",
    "remote role",
    "remote position",
    "remote friendly",
    "remote-friendly",
    "work from home",
    "work from anywhere",
    "work anywhere",
    "workplace flexibility",
    "flexible working hours & workplace",
    "flexible working hours and workplace",
    "flexible workplace",
    "virtual-spain",
]
REMOTE_AMBIGUOUS_PATTERNS = [
    "remote / hybrid",
    "remote/hybrid",
    "remote or hybrid",
    "hybrid or remote",
]
REMOTE_NEGATIVE_PATTERNS = [
    "hybrid",
    "onsite",
    "on-site",
    "office days",
    "in office",
]
CONTRACT_PATTERNS = [
    "full-time",
    "full time",
    "permanent",
    "contract",
    "contractor",
    "freelance",
    "employee",
]
EMPLOYMENT_BENEFIT_PATTERNS = [
    "new hire stock equity",
    "employee stock purchase plan",
    "employee resource groups",
]
MODELING_PATTERNS = [
    "design, train",
    "train",
    "fine-tun",
    "build models",
    "model development",
    "machine learning model",
    "deep learning model",
    "computer vision",
    "nlp",
    "recommender",
    "pytorch",
    "tensorflow",
    "llm",
]
DEPLOYMENT_PATTERNS = [
    "deploy",
    "production",
    "monitor",
    "serving",
    "inference",
    "ci/cd",
    "mlops",
    "deployment pipeline",
]
OPS_ONLY_PATTERNS = [
    "mlops platform",
    "inference platform",
    "serving infrastructure",
    "developer tooling",
    "observability",
    "platform engineering",
    "deployment tooling",
]
OPS_ONLY_ROLE_TOKENS = [
    "mlops",
    "platform",
    "infrastructure",
    "tooling",
    "sre",
    "devops",
]


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        self._href = values.get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        text = re.sub(r"\s+", " ", "".join(self._text_parts)).strip()
        self.anchors.append({"href": self._href, "text": text})
        self._href = None
        self._text_parts = []


def utc_now() -> str:
    return career_shared.utc_now()


def today_date() -> str:
    return career_shared.today_date()


def normalize_text(value: str) -> str:
    return career_shared.normalize_text(value)


def slugify(value: str) -> str:
    return career_shared.slugify(value)


def stable_json_hash(payload: Any) -> str:
    return career_shared.stable_json_hash(payload)


def read_yaml(path: Path) -> dict[str, Any]:
    return career_shared.read_yaml(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return career_shared.load_jsonl(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    career_shared.append_jsonl(path, row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    career_shared.write_jsonl(path, rows)


def get_dotted(mapping: dict[str, Any], dotted_path: str) -> Any:
    return career_shared.get_dotted(mapping, dotted_path)


def is_missing(value: Any) -> bool:
    return career_shared.is_missing(value)


def split_sections(cv_text: str) -> dict[str, list[str]]:
    return career_shared.split_sections(cv_text)


def parse_focus_roles(section_lines: list[str]) -> list[str]:
    return career_shared.parse_focus_roles(section_lines)


def parse_focus_strengths(section_lines: list[str]) -> list[str]:
    return career_shared.parse_focus_strengths(section_lines)


def parse_skills(section_lines: list[str]) -> list[str]:
    return career_shared.parse_skills(section_lines)


def parse_summary_points(section_lines: list[str]) -> list[str]:
    return career_shared.parse_summary_points(section_lines)


def unique_preserve_order(values: list[str]) -> list[str]:
    return career_shared.unique_preserve_order(values)


def extract_candidate_context(cv_text: str) -> dict[str, Any]:
    return career_shared.extract_candidate_context(cv_text)


def build_search_brief(profile: dict[str, Any]) -> dict[str, Any]:
    blocking_questions: list[dict[str, Any]] = []
    recommended_questions: list[dict[str, Any]] = []
    brief: dict[str, Any] = {}

    for field in BRIEF_FIELDS:
        value = get_dotted(profile, field["path"])
        brief[field["path"]] = value
        if not is_missing(value):
            continue
        question = {
            "path": field["path"],
            "question": field["question"],
            "blocking": field["blocking"],
        }
        if field["blocking"]:
            blocking_questions.append(question)
        else:
            recommended_questions.append(question)

    return {
        "generated_at": utc_now(),
        "complete": not blocking_questions,
        "blocking_questions": blocking_questions,
        "recommended_questions": recommended_questions,
        "brief": brief,
    }


def build_search_queries(plan: dict[str, Any]) -> dict[str, list[str]]:
    role_terms = plan["target_role_families"] or ["Machine Learning Engineer"]
    domain_terms = plan["domain_priority"][:3]
    geography = plan["location_filters"].get("hireable_from") or []
    location_term = geography[0] if geography else ""
    remote_mode = plan["location_filters"].get("remote_mode") or ""

    linkedin_queries: list[str] = []
    ats_queries: list[str] = []
    web_queries: list[str] = []

    for role in role_terms[:4]:
        location_bits = " ".join(bit for bit in [location_term, remote_mode.replace("_", " ")] if bit)
        domain_bits = " ".join(domain_terms)
        linkedin_queries.append(f'"{role}" {location_bits} {domain_bits} jobs')
        ats_queries.append(f'site:boards.greenhouse.io "{role}" {location_bits} {domain_bits}'.strip())
        ats_queries.append(f'site:jobs.lever.co "{role}" {location_bits} {domain_bits}'.strip())
        ats_queries.append(f'site:jobs.ashbyhq.com "{role}" {location_bits} {domain_bits}'.strip())
        web_queries.append(f'"{role}" {location_bits} ("careers" OR "jobs") {domain_bits}'.strip())

    return {
        "linkedin_public": unique_preserve_order(linkedin_queries),
        "structured_search": unique_preserve_order(ats_queries),
        "web_search": unique_preserve_order(web_queries),
    }


def derive_query_plan(cv_text: str, profile: dict[str, Any], bias: str = "balanced") -> dict[str, Any]:
    brief = build_search_brief(profile)
    context = extract_candidate_context(cv_text)

    preferred_domains = get_dotted(profile, "preferences.confirmed.search.domains.preferred") or []
    preferred_companies = get_dotted(profile, "preferences.confirmed.search.company_preferences.preferred") or []
    blocked_companies = get_dotted(profile, "preferences.confirmed.search.company_preferences.blocked_confirmed") or []
    rejected_contracts = get_dotted(profile, "preferences.confirmed.search.contract.reject") or []
    allowed_contracts = get_dotted(profile, "preferences.confirmed.search.contract.allowed") or []
    source_priority = get_dotted(profile, "preferences.confirmed.search.discovery.source_priority") or DEFAULT_SOURCE_PRIORITY
    geography = get_dotted(profile, "preferences.confirmed.search.geography") or {}
    remote_policy = get_dotted(profile, "preferences.confirmed.search.remote_policy") or {}

    positive_keywords = unique_preserve_order(
        context["strengths"] + context["skills"] + preferred_domains + context["summary_points"]
    )
    negative_keywords = unique_preserve_order(rejected_contracts)

    plan = {
        "generated_at": utc_now(),
        "bias": bias,
        "is_partial": not brief["complete"],
        "blocking_questions": brief["blocking_questions"],
        "recommended_questions": brief["recommended_questions"],
        "target_role_families": unique_preserve_order(context["target_roles"]),
        "positive_keywords": positive_keywords,
        "negative_keywords": negative_keywords,
        "location_filters": {
            "base": geography.get("base"),
            "hireable_from": geography.get("hireable_from") or [],
            "require_explicit_hiring_scope": geography.get("require_explicit_spain_hiring"),
            "remote_mode": remote_policy.get("mode"),
        },
        "contract_filters": {
            "allowed": allowed_contracts,
            "rejected": rejected_contracts,
        },
        "domain_priority": unique_preserve_order(preferred_domains),
        "company_priority": {
            "preferred": unique_preserve_order(preferred_companies),
            "blocked": unique_preserve_order(blocked_companies),
        },
        "source_priority": unique_preserve_order(source_priority),
    }
    plan["recommended_search_queries"] = build_search_queries(plan)
    plan["plan_id"] = stable_json_hash(plan)[:12]
    return plan


def build_seed_fingerprint(source_catalog: list[dict[str, Any]], seed_urls: list[str]) -> str:
    payload = {
        "source_catalog": source_catalog,
        "seed_urls": sorted(seed_urls),
    }
    return stable_json_hash(payload)[:12]


def maybe_reuse_existing_run(
    plan_id: str,
    seed_fingerprint: str,
    search_runs_path: Path,
    reuse_window_hours: int = 24,
) -> dict[str, Any] | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=reuse_window_hours)
    candidates = [
        row
        for row in load_jsonl(search_runs_path)
        if row.get("plan_id") == plan_id and row.get("seed_fingerprint") == seed_fingerprint
    ]
    candidates.sort(key=lambda row: row.get("recorded_at", ""), reverse=True)
    for row in candidates:
        recorded_at = row.get("recorded_at")
        if not recorded_at:
            continue
        try:
            recorded_dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if recorded_dt >= cutoff:
            return row
    return None


def build_search_run_row(
    *,
    plan: dict[str, Any],
    seed_fingerprint: str,
    sources_consulted: list[str],
    counts: dict[str, int],
    status: str,
    reasons: list[str],
    reused_run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "recorded_at": utc_now(),
        "search_run_id": f"run_{today_date().replace('-', '')}_{stable_json_hash([plan['plan_id'], seed_fingerprint, utc_now()])[:8]}",
        "plan_id": plan["plan_id"],
        "seed_fingerprint": seed_fingerprint,
        "query_plan": plan,
        "sources_consulted": sources_consulted,
        "counts": counts,
        "status": status,
        "reasons": reasons,
        "reused_run_id": reused_run_id,
    }


def load_source_catalog(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = read_yaml(path)
    if isinstance(data, dict):
        return data.get("sources", []) or []
    if isinstance(data, list):
        return data
    return []


def detect_source_kind(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if "greenhouse.io" in host:
        return "greenhouse"
    if "lever.co" in host:
        return "lever"
    if "ashbyhq.com" in host:
        return "ashby_public"
    if "linkedin.com" in host:
        return "linkedin_public"
    return "company_html"


def normalize_seed_url(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    parts = [part for part in parsed.path.split("/") if part]

    if "greenhouse.io" in host:
        token = parts[0] if parts else ""
        return {
            "source_kind": "greenhouse",
            "label": token or host,
            "board_token": token,
            "seed_url": url,
        }
    if "lever.co" in host:
        site = parts[0] if parts else ""
        return {
            "source_kind": "lever",
            "label": site or host,
            "site": site,
            "seed_url": url,
        }
    if "ashbyhq.com" in host:
        board_name = parts[0] if parts else ""
        return {
            "source_kind": "ashby_public",
            "label": board_name or host,
            "board_name": board_name,
            "seed_url": url,
        }
    return {
        "source_kind": detect_source_kind(url),
        "label": host or url,
        "careers_url": url,
        "seed_url": url,
    }


def aggregator_url(url: str | None) -> bool:
    if not url:
        return False
    host = urllib.parse.urlparse(url).netloc.lower()
    return host in AGGREGATOR_HOSTS


def http_get(url: str, *, accept: str = "text/html") -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CodexCareerAgent/2.0 (+https://developers.openai.com/codex)",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        charset_match = re.search(r"charset=([A-Za-z0-9_-]+)", content_type)
        charset = charset_match.group(1) if charset_match else "utf-8"
        return body.decode(charset, errors="replace"), content_type


def strip_tags(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def collect_anchors(html: str, base_url: str) -> list[dict[str, str]]:
    parser = AnchorCollector()
    parser.feed(html)
    anchors: list[dict[str, str]] = []
    for anchor in parser.anchors:
        href = anchor["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        anchors.append({"href": absolute, "text": anchor["text"]})
    return anchors


def match_query_plan(title: str, snippet: str, location: str, plan: dict[str, Any]) -> bool:
    combined = normalize_text(" ".join([title, snippet, location]))
    target_roles = [normalize_text(role) for role in plan.get("target_role_families", [])]
    positive_keywords = [normalize_text(keyword) for keyword in plan.get("positive_keywords", [])]

    role_match = not target_roles or any(role and role in combined for role in target_roles)
    positive_hits = sum(1 for keyword in positive_keywords if keyword and keyword in combined)

    if plan.get("bias") == "coverage_first":
        return role_match or positive_hits >= 1
    if plan.get("bias") == "precision_first":
        return role_match and (positive_hits >= 1 or not positive_keywords)
    return role_match or positive_hits >= 2 or not positive_keywords


def normalize_candidate(
    *,
    source_kind: str,
    source_record_id: str,
    company: str,
    role: str,
    discovery_url: str,
    posted_at: str | None,
    location_text: str | None,
    raw_snippet: str,
    source_confidence: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = {
        "source_kind": source_kind,
        "source_record_id": source_record_id,
        "company": company,
        "role": role,
        "discovery_url": discovery_url,
        "posted_at": posted_at,
        "location_text": location_text,
        "raw_snippet": raw_snippet,
        "source_confidence": source_confidence,
    }
    if extra:
        candidate.update(extra)
    return candidate


def discover_greenhouse(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    board_token = config.get("board_token")
    if not board_token:
        raise ValueError("greenhouse source requires board_token")
    raw_json, _ = http_get(
        f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
        accept="application/json",
    )
    payload = json.loads(raw_json)
    company_label = config.get("company") or config.get("label") or board_token
    candidates: list[dict[str, Any]] = []
    for job in payload.get("jobs", []):
        location = (job.get("location") or {}).get("name")
        snippet = strip_tags(job.get("content", ""))
        if not match_query_plan(job.get("title", ""), snippet, location or "", plan):
            continue
        candidates.append(
            normalize_candidate(
                source_kind="greenhouse",
                source_record_id=str(job.get("id")),
                company=company_label,
                role=job.get("title", ""),
                discovery_url=job.get("absolute_url", config.get("seed_url", "")),
                posted_at=job.get("updated_at"),
                location_text=location,
                raw_snippet=snippet[:1200],
                source_confidence="high",
                extra={
                    "detail_url": job.get("absolute_url"),
                    "board_token": board_token,
                    "detail_text": snippet[:4000],
                },
            )
        )
    return candidates


def discover_lever(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    site = config.get("site")
    if not site:
        raise ValueError("lever source requires site")
    raw_json, _ = http_get(
        f"https://api.lever.co/v0/postings/{site}?mode=json&limit=100",
        accept="application/json",
    )
    payload = json.loads(raw_json)
    company_label = config.get("company") or config.get("label") or site
    candidates: list[dict[str, Any]] = []
    for job in payload:
        categories = job.get("categories") or {}
        location = categories.get("location")
        description = strip_tags(job.get("descriptionPlain") or job.get("description") or "")
        if not match_query_plan(job.get("text", ""), description, location or "", plan):
            continue
        candidates.append(
            normalize_candidate(
                source_kind="lever",
                source_record_id=str(job.get("id")),
                company=company_label,
                role=job.get("text", ""),
                discovery_url=job.get("hostedUrl", config.get("seed_url", "")),
                posted_at=job.get("createdAt"),
                location_text=location,
                raw_snippet=description[:1200],
                source_confidence="high",
                extra={
                    "detail_url": job.get("hostedUrl"),
                    "site": site,
                    "detail_text": description[:4000],
                },
            )
        )
    return candidates


def discover_ashby_public(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    board_name = config.get("board_name")
    seed_url = config.get("seed_url")
    if board_name:
        url = f"https://jobs.ashbyhq.com/{board_name}"
    elif seed_url:
        url = seed_url
    else:
        raise ValueError("ashby_public source requires board_name or seed_url")

    html, _ = http_get(url)
    anchors = collect_anchors(html, url)
    candidates: list[dict[str, Any]] = []
    company_label = config.get("company") or config.get("label") or board_name or urllib.parse.urlparse(url).netloc

    for anchor in anchors:
        href = anchor["href"]
        title = anchor["text"]
        if "ashbyhq.com" not in urllib.parse.urlparse(href).netloc.lower():
            continue
        if "/job/" not in href and "/jobs/" not in href:
            continue
        if not match_query_plan(title, title, "", plan):
            continue
        record_id = stable_json_hash([company_label, href])[:12]
        candidates.append(
            normalize_candidate(
                source_kind="ashby_public",
                source_record_id=record_id,
                company=company_label,
                role=title or "Untitled role",
                discovery_url=href,
                posted_at=None,
                location_text=None,
                raw_snippet=title,
                source_confidence="medium",
                extra={"detail_url": href},
            )
        )
    return unique_candidates(candidates)


def discover_company_html(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    careers_url = config.get("careers_url") or config.get("seed_url")
    if not careers_url:
        raise ValueError("company_html source requires careers_url or seed_url")
    html, _ = http_get(careers_url)
    anchors = collect_anchors(html, careers_url)
    company_label = config.get("company") or config.get("label") or urllib.parse.urlparse(careers_url).netloc
    candidates: list[dict[str, Any]] = []

    for anchor in anchors:
        href = anchor["href"]
        text = anchor["text"]
        href_lc = href.lower()
        if not text:
            continue
        if not any(token in href_lc for token in ["/job", "/jobs", "/career", "/careers", "greenhouse", "lever", "ashby"]):
            continue
        if not match_query_plan(text, text, "", plan):
            continue
        detected_kind = detect_source_kind(href)
        record_id = stable_json_hash([company_label, href])[:12]
        candidates.append(
            normalize_candidate(
                source_kind=detected_kind if detected_kind != "linkedin_public" else "company_html",
                source_record_id=record_id,
                company=company_label,
                role=text,
                discovery_url=href,
                posted_at=None,
                location_text=None,
                raw_snippet=text,
                source_confidence="medium" if detected_kind != "company_html" else "low",
                extra={"detail_url": href},
            )
        )
    return unique_candidates(candidates)


def discover_linkedin_public(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    seed_url = config.get("seed_url")
    if not seed_url:
        raise ValueError("linkedin_public source requires seed_url")
    title = config.get("title") or urllib.parse.unquote(seed_url.rsplit("/", 1)[-1]).replace("-", " ")
    if not match_query_plan(title, title, "", plan):
        return []
    company = config.get("company") or "LinkedIn discovery"
    record_id = stable_json_hash([seed_url, title])[:12]
    return [
        normalize_candidate(
            source_kind="linkedin_public",
            source_record_id=record_id,
            company=company,
            role=title,
            discovery_url=seed_url,
            posted_at=None,
            location_text=None,
            raw_snippet=title,
            source_confidence="low",
            extra={"detail_url": seed_url},
        )
    ]


ADAPTERS = {
    "greenhouse": discover_greenhouse,
    "lever": discover_lever,
    "ashby_public": discover_ashby_public,
    "company_html": discover_company_html,
    "linkedin_public": discover_linkedin_public,
}


def unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = stable_json_hash(
            [
                candidate.get("source_kind"),
                candidate.get("source_record_id"),
                candidate.get("company"),
                candidate.get("discovery_url"),
            ]
        )
        if key not in by_key:
            by_key[key] = candidate
    return list(by_key.values())


def discover_candidates(
    plan: dict[str, Any],
    *,
    source_catalog: list[dict[str, Any]] | None = None,
    seed_urls: list[str] | None = None,
    max_workers: int = 4,
) -> tuple[list[dict[str, Any]], list[str]]:
    source_catalog = list(source_catalog or [])
    seed_urls = list(seed_urls or [])
    all_configs = source_catalog + [normalize_seed_url(url) for url in seed_urls]

    discovered: list[dict[str, Any]] = []
    consulted_sources: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for config in all_configs:
            source_kind = config.get("source_kind")
            adapter = ADAPTERS.get(source_kind)
            if adapter is None:
                continue
            consulted_sources.append(source_kind)
            future_map[executor.submit(adapter, config, plan)] = source_kind

        for future in as_completed(future_map):
            source_kind = future_map[future]
            try:
                discovered.extend(future.result())
            except (ValueError, urllib.error.URLError, json.JSONDecodeError):
                discovered.append(
                    normalize_candidate(
                        source_kind=source_kind,
                        source_record_id=stable_json_hash([source_kind, utc_now()])[:12],
                        company=source_kind,
                        role="discovery_failed",
                        discovery_url="",
                        posted_at=None,
                        location_text=None,
                        raw_snippet="adapter failed during discovery",
                        source_confidence="low",
                        extra={"discovery_error": True},
                    )
                )

    return unique_candidates(discovered), unique_preserve_order(consulted_sources)


def first_matching_line(text: str, patterns: list[str]) -> str | None:
    for line in split_text_units(text):
        lower = line.lower()
        if any(pattern in lower for pattern in patterns):
            return line
    return None


def split_text_units(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    raw_units = re.split(r"(?<=[.!?])\s+|\s+[•\-]\s+", compact)
    return [unit.strip() for unit in raw_units if unit.strip()]


def looks_country_level_location(location_text: str | None) -> bool:
    if not location_text:
        return False
    normalized = normalize_text(location_text)
    if "remote" in normalized or "virtual" in normalized:
        return True
    if ";" in location_text or "," in location_text:
        return False
    return normalized in {"spain", "es - spain", "madrid, spain", "remote (spain)"} or normalized.endswith(" spain")


def extract_remote_evidence(detail_text: str, location_text: str | None) -> tuple[str | None, str]:
    positive_quote = first_matching_line(detail_text, REMOTE_POSITIVE_PATTERNS)
    ambiguous_quote = first_matching_line(detail_text, REMOTE_AMBIGUOUS_PATTERNS)
    negative_quote = first_matching_line(detail_text, REMOTE_NEGATIVE_PATTERNS)
    location_is_remote = looks_country_level_location(location_text)
    location_remote_quote = f"Location: {location_text}" if location_is_remote and location_text else None

    # Some official pages combine a generic hybrid-culture note with an explicit country-level
    # remote location. In those cases, the specific location is the stronger hiring signal.
    if location_remote_quote:
        return location_remote_quote, "remote"

    if ambiguous_quote:
        return ambiguous_quote, "ambiguous"
    if positive_quote and not negative_quote:
        return positive_quote, "remote"
    if positive_quote and negative_quote:
        if location_remote_quote:
            return location_remote_quote, "remote"
        return positive_quote, "ambiguous"
    if negative_quote:
        return negative_quote, "hybrid_or_onsite"

    if location_is_remote:
        flexible_quote = first_matching_line(detail_text, ["flexible workplace", "workplace flexibility", "flexible working hours"])
        if flexible_quote:
            return f"{flexible_quote} Location: {location_text}", "remote"
        return location_remote_quote, "remote"

    return None, "unknown"


def extract_geography_evidence(detail_text: str, location_text: str | None) -> str | None:
    geography_quote = first_matching_line(
        detail_text,
        ["spain", "europe", "country:", "location:", "remote:", "based in", "hire in"],
    )
    if geography_quote:
        return geography_quote
    if location_text:
        return f"Location: {location_text}"
    return None


def extract_contract_evidence(detail_text: str) -> str | None:
    contract_quote = first_matching_line(detail_text, CONTRACT_PATTERNS)
    if contract_quote:
        return contract_quote

    benefit_quote = first_matching_line(detail_text, EMPLOYMENT_BENEFIT_PATTERNS)
    if benefit_quote:
        return f"{benefit_quote} (employee benefits signal)"

    return None


def detect_ops_only_signal(role: str, detail_text: str) -> str | None:
    role_norm = normalize_text(role)
    if any(token in role_norm for token in OPS_ONLY_ROLE_TOKENS):
        return f"Role title indicates operations/platform scope: {role}"
    return first_matching_line(detail_text, OPS_ONLY_PATTERNS)


def normalize_contract_token(value: str) -> str:
    lowered = value.lower().strip()
    lowered = lowered.replace("-", " ").replace("_", " ")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def extract_salary(text: str) -> tuple[str | None, str | None, str | None]:
    match = re.search(
        r"((?:EUR|USD|GBP|CAD|AUD|CHF|SGD|€|\$|£)\s?[0-9][0-9.,kK]*)\s*(?:-|to|–)\s*((?:EUR|USD|GBP|CAD|AUD|CHF|SGD|€|\$|£)?\s?[0-9][0-9.,kK]*)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None, None
    band = f"{match.group(1)}-{match.group(2)}"
    return band, "Explicit", match.group(0)


def fetch_candidate_detail_text(candidate: dict[str, Any]) -> str:
    if candidate.get("detail_text"):
        return str(candidate["detail_text"])
    detail_url = candidate.get("detail_url") or candidate.get("discovery_url")
    if not detail_url:
        return ""
    html, _ = http_get(detail_url)
    return strip_tags(html)


def evaluate_hard_filters(
    profile: dict[str, Any],
    *,
    remote_quote: str | None,
    remote_state: str,
    geography_quote: str | None,
    contract_quote: str | None,
    modeling_quote: str | None,
    deployment_quote: str | None,
    ops_only_quote: str | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    remote_mode = get_dotted(profile, "preferences.confirmed.search.remote_policy.mode")
    if remote_mode == "remote_only":
        if remote_state == "hybrid_or_onsite":
            return "discarded", ["remote mismatch"]
        if remote_state == "ambiguous":
            reasons.append("remote policy ambiguous")
        elif remote_quote is None:
            reasons.append("remote evidence missing")

    geography = get_dotted(profile, "preferences.confirmed.search.geography") or {}
    hireable_from = [country.lower() for country in geography.get("hireable_from") or []]
    require_explicit = geography.get("require_explicit_spain_hiring")
    if hireable_from and require_explicit:
        if geography_quote is None:
            reasons.append("hiring geography evidence missing")
        elif not any(country in geography_quote.lower() for country in hireable_from):
            return "discarded", ["geography mismatch"]

    allowed_contracts = [
        normalize_contract_token(value)
        for value in (get_dotted(profile, "preferences.confirmed.search.contract.allowed") or [])
    ]
    rejected_contracts = [
        normalize_contract_token(value)
        for value in (get_dotted(profile, "preferences.confirmed.search.contract.reject") or [])
    ]
    if contract_quote is None:
        reasons.append("contract evidence missing")
    else:
        lowered = normalize_contract_token(contract_quote)
        if any(token in lowered for token in rejected_contracts):
            return "discarded", ["contract mismatch"]
        if allowed_contracts and not any(token in lowered for token in allowed_contracts):
            reasons.append("allowed contract evidence missing")

    if get_dotted(profile, "preferences.confirmed.search.role_scope.require_model_development") and modeling_quote is None:
        if ops_only_quote is not None:
            return "discarded", ["model development mismatch"]
        reasons.append("model development evidence missing")
    if get_dotted(profile, "preferences.confirmed.search.role_scope.require_production_ownership") and deployment_quote is None:
        reasons.append("production ownership evidence missing")

    if reasons:
        return "pending", reasons
    return "new", []


def compute_soft_score(profile: dict[str, Any], candidate: dict[str, Any], detail_text: str) -> int:
    score = 0
    preferred_domains = [value.lower() for value in (get_dotted(profile, "preferences.confirmed.search.domains.preferred") or [])]
    preferred_companies = [value.lower() for value in (get_dotted(profile, "preferences.confirmed.search.company_preferences.preferred") or [])]
    combined = normalize_text(" ".join([candidate.get("role", ""), candidate.get("raw_snippet", ""), detail_text]))

    score += {"high": 3, "medium": 2, "low": 1}.get(candidate.get("source_confidence"), 0)
    if candidate.get("company", "").lower() in preferred_companies:
        score += 3
    score += sum(1 for domain in preferred_domains if domain in combined)
    if first_matching_line(detail_text, DEPLOYMENT_PATTERNS):
        score += 1
    return score


def verify_and_rank_candidates(
    candidates: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    search_run_id: str,
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []

    for candidate in candidates:
        if candidate.get("discovery_error"):
            continue

        detail_text = fetch_candidate_detail_text(candidate)
        remote_quote, remote_state = extract_remote_evidence(detail_text, candidate.get("location_text"))
        geography_quote = extract_geography_evidence(detail_text, candidate.get("location_text"))
        contract_quote = extract_contract_evidence(detail_text)
        modeling_quote = first_matching_line(detail_text, MODELING_PATTERNS)
        deployment_quote = first_matching_line(detail_text, DEPLOYMENT_PATTERNS)
        ops_only_quote = detect_ops_only_signal(candidate.get("role", ""), detail_text)
        salary_band, salary_basis, salary_evidence = extract_salary(detail_text)
        status, reasons = evaluate_hard_filters(
            profile,
            remote_quote=remote_quote,
            remote_state=remote_state,
            geography_quote=geography_quote,
            contract_quote=contract_quote,
            modeling_quote=modeling_quote,
            deployment_quote=deployment_quote,
            ops_only_quote=ops_only_quote,
        )
        evidence_urls = unique_preserve_order(
            [value for value in [candidate.get("detail_url"), candidate.get("discovery_url")] if value]
        )
        soft_score = compute_soft_score(profile, candidate, detail_text)
        verification_confidence = "high" if candidate.get("source_confidence") == "high" and not reasons else "medium"
        if candidate.get("source_confidence") == "low":
            verification_confidence = "low"

        verified.append(
            {
                "dedupe_key": f"{slugify(candidate.get('company', 'unknown'))}__{slugify(candidate.get('role', 'unknown'))}",
                "company": candidate.get("company"),
                "role": candidate.get("role"),
                "status": status,
                "discovery_url": candidate.get("discovery_url"),
                "final_company_apply_url": None if aggregator_url(candidate.get("detail_url")) else candidate.get("detail_url"),
                "remote_policy_quote": remote_quote,
                "contract_type_signal": contract_quote,
                "spain_hiring_quote": geography_quote,
                "deep_learning_scope_quote": modeling_quote,
                "deployment_scope_quote": deployment_quote,
                "salary_band": salary_band,
                "salary_basis": salary_basis,
                "salary_confidence": "High" if salary_band else None,
                "salary_evidence": salary_evidence,
                "consulting_risk": None,
                "user_note": None,
                "review_required": status == "pending",
                "review_reason": "; ".join(reasons) if reasons else None,
                "source_kind": candidate.get("source_kind"),
                "source_record_id": candidate.get("source_record_id"),
                "evidence_urls": evidence_urls,
                "first_seen_at": today_date(),
                "last_seen_at": today_date(),
                "search_run_id": search_run_id,
                "verification_confidence": verification_confidence,
                "source_confidence": candidate.get("source_confidence"),
                "soft_score": soft_score,
                "raw_snippet": candidate.get("raw_snippet"),
            }
        )

    verified.sort(key=lambda row: (row["status"] != "new", -row["soft_score"], row["company"], row["role"]))
    return verified
