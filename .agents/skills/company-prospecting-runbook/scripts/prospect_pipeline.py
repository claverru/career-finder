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


SCRIPT_DIR = Path(__file__).resolve().parent
COMMON_DIR = SCRIPT_DIR.parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

import career_shared


CAREER_ROOT = career_shared.CAREER_ROOT
DEFAULT_PROFILE_PATH = career_shared.DEFAULT_PROFILE_PATH
DEFAULT_CV_PATH = career_shared.DEFAULT_CV_PATH
career_shared.ensure_state_layout()
DEFAULT_PROSPECT_RUNS_PATH = career_shared.PROSPECT_RUNS_PATH
DEFAULT_DISCOVERY_OUTPUT_PATH = career_shared.PROSPECT_DISCOVERY_CANDIDATES_PATH
DEFAULT_RANKED_OUTPUT_PATH = career_shared.PROSPECT_RANKED_PROSPECTS_PATH
DEFAULT_CONTACT_OUTPUT_PATH = career_shared.PROSPECT_RESOLVED_CONTACTS_PATH
DEFAULT_SOURCE_CATALOG_PATH = CAREER_ROOT / "prospecting" / "policy" / "source_catalog.yaml"
DEFAULT_SOURCE_PRIORITY = [
    "leaderboard",
    "funding_roundup",
    "company_directory",
    "company_html",
    "public_people",
    "linkedin_company",
    "web_search",
]
BRIEF_FIELDS = [
    {
        "path": "preferences.confirmed.search.remote_policy.mode",
        "question": "What remote policy should the prospecting run use?",
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
        "question": "Are there any companies that should be blocked for future prospecting?",
        "blocking": False,
    },
]
REMOTE_POSITIVE_PATTERNS = [
    "remote",
    "remote only",
    "remote-only",
    "remote friendly",
    "remote-friendly",
    "work from anywhere",
    "work anywhere",
    "workplace flexibility",
    "flexible workplace",
    "flexible working hours & workplace",
    "flexible working hours and workplace",
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
GEOGRAPHY_PATTERNS = [
    "spain",
    "europe",
    "european union",
    "eu ai act",
    "emea",
    "remote from",
    "based in",
    "hire in",
    "work from",
]
EU_COUNTRY_PATTERNS = [
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czech republic",
    "czechia",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
]
EU_REGION_PATTERNS = [
    "europe",
    "european union",
    "eu ai act",
    "eu-based",
    "eu based",
] + EU_COUNTRY_PATTERNS
SPAIN_PRESENCE_PATTERNS = [
    "spain",
    "madrid",
    "barcelona",
    "valencia",
    "malaga",
    "bilbao",
    "seville",
    "sevilla",
]
GROWTH_PATTERNS = [
    "fast-growing",
    "high-growth",
    "growing",
    "growth",
    "scaling",
    "expanding",
    "backed by",
    "series a",
    "series b",
    "series c",
    "funded",
    "raised",
    "customers",
    "revenue",
    "leaderboard",
]
PRODUCT_PATTERNS = [
    "platform",
    "product",
    "technology",
    "software",
    "ai",
    "artificial intelligence",
    "machine learning",
    "model",
]
TEAM_PATTERNS = [
    "team",
    "build",
    "building",
    "hiring",
    "recruiting",
    "people",
    "function",
    "department",
]
FOUNDER_ELIGIBILITY_PATTERNS = [
    "startup",
    "small team",
    "lean team",
    "founding team",
    "early-stage",
    "series a",
    "seed",
    "venture-backed",
]
GENERIC_ANCHOR_TOKENS = {
    "about",
    "blog",
    "careers",
    "contact",
    "cookie",
    "cookies",
    "download",
    "follow",
    "home",
    "jobs",
    "learn more",
    "legal",
    "login",
    "privacy",
    "read more",
    "sign in",
    "terms",
}
PAGE_HINT_TOKENS = [
    "about",
    "careers",
    "contact",
    "jobs",
    "join",
    "people",
    "team",
    "work",
]
RECRUITING_PATTERNS = [
    "talent",
    "recruit",
    "people partner",
    "people ops",
    "hiring",
    "human resources",
    "hr",
]
FOUNDER_PATTERNS = [
    "founder",
    "co-founder",
    "ceo",
    "general manager",
]
LEAD_PATTERNS = [
    "lead",
    "head",
    "manager",
    "director",
    "vp",
    "principal",
]
STOPWORDS = {
    "and",
    "applied",
    "engineer",
    "head",
    "lead",
    "manager",
    "of",
    "principal",
    "senior",
    "staff",
    "the",
    "to",
    "with",
}


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


def unique_preserve_order(values: list[str]) -> list[str]:
    return career_shared.unique_preserve_order(values)


def extract_candidate_context(cv_text: str) -> dict[str, Any]:
    return career_shared.extract_candidate_context(cv_text)


def build_prospect_brief(profile: dict[str, Any]) -> dict[str, Any]:
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


def summarize_terms(values: list[str], limit: int = 3) -> str:
    return " ".join(unique_preserve_order(values)[:limit])


def build_discovery_queries(plan: dict[str, Any]) -> dict[str, list[str]]:
    role_terms = plan["target_role_families"] or ["Growth"]
    focus_terms = plan["focus_topics"][:3]
    geography = plan["location_filters"].get("hireable_from") or []
    location_term = geography[0] if geography else ""

    company_queries: list[str] = []
    contact_queries: list[str] = []

    for role in role_terms[:4]:
        topic_bits = summarize_terms(focus_terms)
        location_bits = " ".join(bit for bit in [location_term, plan["location_filters"].get("remote_mode")] if bit)
        company_queries.append(f'"{role}" {topic_bits} {location_bits} company'.strip())
        contact_queries.append(
            f'"{role}" {topic_bits} recruiter OR hiring OR team lead {location_bits}'.strip()
        )

    return {
        "company_discovery": unique_preserve_order(company_queries),
        "contact_discovery": unique_preserve_order(contact_queries),
    }


def derive_prospect_plan(
    cv_text: str,
    profile: dict[str, Any],
    *,
    bias: str = "balanced",
    themes: list[str] | None = None,
    target_roles: list[str] | None = None,
) -> dict[str, Any]:
    brief = build_prospect_brief(profile)
    context = extract_candidate_context(cv_text)

    preferred_domains = get_dotted(profile, "preferences.confirmed.search.domains.preferred") or []
    preferred_companies = get_dotted(profile, "preferences.confirmed.search.company_preferences.preferred") or []
    blocked_companies = get_dotted(profile, "preferences.confirmed.search.company_preferences.blocked_confirmed") or []
    geography = get_dotted(profile, "preferences.confirmed.search.geography") or {}
    remote_policy = get_dotted(profile, "preferences.confirmed.search.remote_policy") or {}
    source_priority = (
        get_dotted(profile, "preferences.confirmed.prospecting.discovery.source_priority")
        or DEFAULT_SOURCE_PRIORITY
    )

    role_families = unique_preserve_order(list(target_roles or []) + context["target_roles"])
    if not role_families and context["headline"]:
        role_families = [context["headline"]]

    focus_topics = unique_preserve_order(
        list(themes or []) + preferred_domains + context["strengths"] + context["skills"]
    )
    positive_keywords = unique_preserve_order(role_families + focus_topics + context["summary_points"])

    plan = {
        "generated_at": utc_now(),
        "bias": bias,
        "is_partial": not brief["complete"],
        "blocking_questions": brief["blocking_questions"],
        "recommended_questions": brief["recommended_questions"],
        "target_role_families": role_families,
        "focus_topics": focus_topics,
        "positive_keywords": positive_keywords,
        "negative_keywords": unique_preserve_order(blocked_companies),
        "location_filters": {
            "base": geography.get("base"),
            "hireable_from": geography.get("hireable_from") or [],
            "require_explicit_hiring_scope": geography.get("require_explicit_spain_hiring"),
            "remote_mode": remote_policy.get("mode"),
        },
        "company_priority": {
            "preferred": unique_preserve_order(preferred_companies),
            "blocked": unique_preserve_order(blocked_companies),
        },
        "domain_priority": unique_preserve_order(preferred_domains),
        "source_priority": unique_preserve_order(source_priority),
        "explicit_theme_focus": unique_preserve_order(list(themes or [])),
    }
    plan["recommended_search_queries"] = build_discovery_queries(plan)
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
    prospect_runs_path: Path,
    reuse_window_hours: int = 24,
) -> dict[str, Any] | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=reuse_window_hours)
    candidates = [
        row
        for row in load_jsonl(prospect_runs_path)
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


def build_prospect_run_row(
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
        "prospect_run_id": f"run_{today_date().replace('-', '')}_{stable_json_hash([plan['plan_id'], seed_fingerprint, utc_now()])[:8]}",
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
    path = parsed.path.lower()
    if "linkedin.com" in host and "/company/" in path:
        return "linkedin_company"
    if "linkedin.com" in host and ("/in/" in path or "/pub/" in path):
        return "public_people"
    if "leaderboard" in path or "ranking" in path or "sifted.eu" in host:
        return "leaderboard"
    if "funding" in path or "roundup" in path or "raise" in path:
        return "funding_roundup"
    if any(token in path for token in ["/team", "/people", "/leadership"]):
        return "public_people"
    return "company_html"


def normalize_seed_url(url: str) -> dict[str, Any]:
    source_kind = detect_source_kind(url)
    host = urllib.parse.urlparse(url).netloc.lower()
    return {
        "source_kind": source_kind,
        "label": host or url,
        "seed_url": url,
        "listing_url": url if source_kind in {"leaderboard", "funding_roundup", "company_directory"} else None,
        "company_url": url if source_kind == "company_html" else None,
    }


def http_get(url: str, *, accept: str = "text/html") -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CodexCareerAgent/3.0 (+https://developers.openai.com/codex)",
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
    value = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", value)
    value = re.sub(r"(?i)</\s*(p|div|li|section|article|h[1-6]|tr|td|ul|ol)\s*>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s*", "\n", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()


def html_to_text(html: str) -> str:
    return strip_tags(html)


def collect_anchors(html: str, base_url: str) -> list[dict[str, str]]:
    parser = AnchorCollector()
    parser.feed(html)
    anchors: list[dict[str, str]] = []
    for anchor in parser.anchors:
        href = anchor["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        anchors.append({"href": absolute, "text": anchor["text"]})
    return anchors


def collect_mailtos(html: str) -> list[str]:
    emails: list[str] = []
    for match in re.finditer(r'href=["\']mailto:([^"\']+)["\']', html, flags=re.IGNORECASE):
        email = match.group(1).split("?", 1)[0].strip()
        if email:
            emails.append(email)
    return unique_preserve_order(emails)


def extract_page_title(html: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", strip_tags(match.group(1))).strip() or None


def looks_like_company_name(text: str) -> bool:
    cleaned = text.strip()
    normalized = normalize_text(cleaned)
    if not normalized or normalized in GENERIC_ANCHOR_TOKENS:
        return False
    if len(cleaned) < 2 or len(cleaned) > 80:
        return False
    if cleaned.count(" ") > 6:
        return False
    if "@" in cleaned or "/" in cleaned:
        return False
    return True


def label_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    label = host.split(".", 1)[0].replace("-", " ").strip()
    return label.title() or host


def source_confidence_for_kind(source_kind: str) -> str:
    return {
        "leaderboard": "high",
        "funding_roundup": "high",
        "company_directory": "medium",
        "company_html": "high",
        "public_people": "medium",
        "linkedin_company": "low",
    }.get(source_kind, "low")


def normalize_candidate(
    *,
    source_kind: str,
    source_record_id: str,
    company: str,
    discovery_url: str,
    raw_snippet: str,
    source_confidence: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = {
        "source_kind": source_kind,
        "source_record_id": source_record_id,
        "company": company,
        "discovery_url": discovery_url,
        "raw_snippet": raw_snippet,
        "source_confidence": source_confidence,
    }
    if extra:
        candidate.update(extra)
    return candidate


def discover_listing_source(config: dict[str, Any], plan: dict[str, Any], source_kind: str) -> list[dict[str, Any]]:
    listing_url = config.get("listing_url") or config.get("seed_url")
    if not listing_url:
        raise ValueError(f"{source_kind} source requires listing_url or seed_url")
    html, _ = http_get(listing_url)
    anchors = collect_anchors(html, listing_url)
    listing_text = html_to_text(html)

    if config.get("company"):
        company = config["company"]
        return [
            normalize_candidate(
                source_kind=source_kind,
                source_record_id=stable_json_hash([source_kind, listing_url, company])[:12],
                company=company,
                discovery_url=listing_url,
                raw_snippet=listing_text[:1200],
                source_confidence=source_confidence_for_kind(source_kind),
                extra={
                    "detail_url": config.get("detail_url") or config.get("company_url") or listing_url,
                    "company_url": config.get("company_url") or config.get("detail_url") or listing_url,
                },
            )
        ]

    candidates: list[dict[str, Any]] = []
    for anchor in anchors:
        if not looks_like_company_name(anchor["text"]):
            continue
        detail_url = anchor["href"]
        company = anchor["text"].strip()
        candidates.append(
            normalize_candidate(
                source_kind=source_kind,
                source_record_id=stable_json_hash([source_kind, listing_url, company, detail_url])[:12],
                company=company,
                discovery_url=listing_url,
                raw_snippet=f"{company} {listing_text[:600]}".strip(),
                source_confidence=source_confidence_for_kind(source_kind),
                extra={
                    "detail_url": detail_url,
                    "company_url": detail_url,
                },
            )
        )
        if len(candidates) >= 40:
            break
    return unique_candidates(candidates)


def discover_company_html(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    company_url = config.get("company_url") or config.get("careers_url") or config.get("seed_url")
    if not company_url:
        raise ValueError("company_html source requires company_url, careers_url, or seed_url")
    html, _ = http_get(company_url)
    text = html_to_text(html)
    title = extract_page_title(html) or label_from_url(company_url)
    company = config.get("company") or title.split("|", 1)[0].split(" - ", 1)[0].strip() or label_from_url(company_url)
    return [
        normalize_candidate(
            source_kind="company_html",
            source_record_id=stable_json_hash(["company_html", company_url, company])[:12],
            company=company,
            discovery_url=company_url,
            raw_snippet=text[:1200],
            source_confidence="high" if config.get("company") else "medium",
            extra={
                "detail_url": company_url,
                "company_url": company_url,
                "contact_page_urls": config.get("contact_page_urls") or [],
                "people_page_urls": config.get("people_page_urls") or [],
            },
        )
    ]


def discover_linkedin_company(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    seed_url = config.get("seed_url")
    if not seed_url:
        raise ValueError("linkedin_company source requires seed_url")
    company = config.get("company") or label_from_url(seed_url)
    return [
        normalize_candidate(
            source_kind="linkedin_company",
            source_record_id=stable_json_hash(["linkedin_company", seed_url, company])[:12],
            company=company,
            discovery_url=seed_url,
            raw_snippet=company,
            source_confidence="low",
            extra={
                "detail_url": seed_url,
                "company_url": seed_url,
            },
        )
    ]


def discover_public_people(config: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    seed_url = config.get("seed_url")
    if not seed_url:
        raise ValueError("public_people source requires seed_url")
    company = config.get("company") or label_from_url(seed_url)
    return [
        normalize_candidate(
            source_kind="public_people",
            source_record_id=stable_json_hash(["public_people", seed_url, company])[:12],
            company=company,
            discovery_url=seed_url,
            raw_snippet=company,
            source_confidence="medium",
            extra={
                "detail_url": config.get("company_url") or seed_url,
                "company_url": config.get("company_url") or seed_url,
                "people_page_urls": [seed_url],
            },
        )
    ]


ADAPTERS = {
    "leaderboard": lambda config, plan: discover_listing_source(config, plan, "leaderboard"),
    "funding_roundup": lambda config, plan: discover_listing_source(config, plan, "funding_roundup"),
    "company_directory": lambda config, plan: discover_listing_source(config, plan, "company_directory"),
    "company_html": discover_company_html,
    "linkedin_company": discover_linkedin_company,
    "public_people": discover_public_people,
}


def unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = stable_json_hash(
            [
                candidate.get("source_kind"),
                candidate.get("company"),
                candidate.get("detail_url"),
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
                        discovery_url="",
                        raw_snippet="adapter failed during discovery",
                        source_confidence="low",
                        extra={"discovery_error": True},
                    )
                )

    return unique_candidates(discovered), unique_preserve_order(consulted_sources)


def split_text_units(text: str) -> list[str]:
    if not text:
        return []
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return unique_preserve_order(lines + [sentence.strip() for sentence in sentences if sentence.strip()])


def first_matching_line(text: str, patterns: list[str]) -> str | None:
    normalized_patterns = [normalize_text(pattern) for pattern in patterns if pattern]
    for line in split_text_units(text):
        lower = normalize_text(line)
        if any(pattern and pattern in lower for pattern in normalized_patterns):
            return line
    return None


def looks_country_level_location(location_text: str | None) -> bool:
    if not location_text:
        return False
    normalized = normalize_text(location_text)
    if "remote" in normalized or "virtual" in normalized:
        return True
    if ";" in location_text or "," in location_text:
        return False
    return normalized in {"spain", "es - spain", "remote (spain)"} or normalized.endswith(" spain")


def extract_remote_evidence(detail_text: str, location_text: str | None) -> tuple[str | None, str]:
    positive_quote = first_matching_line(detail_text, REMOTE_POSITIVE_PATTERNS)
    ambiguous_quote = first_matching_line(detail_text, REMOTE_AMBIGUOUS_PATTERNS)
    negative_quote = first_matching_line(detail_text, REMOTE_NEGATIVE_PATTERNS)
    location_is_remote = looks_country_level_location(location_text)
    location_remote_quote = f"Location: {location_text}" if location_is_remote and location_text else None

    # Some official pages mix a generic hybrid-culture note with an explicit country-level
    # remote location. Prefer the specific hiring location when both appear together.
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
        return location_remote_quote, "remote"
    return None, "unknown"


def extract_geography_evidence(detail_text: str, location_text: str | None) -> str | None:
    units = split_text_units(detail_text)
    for pattern_group in [
        ["spain", "hire in", "work from", "remote from", "based in"],
        ["europe", "emea"],
    ]:
        for line in units:
            lower = normalize_text(line)
            if any(pattern in lower for pattern in pattern_group):
                return line
    if location_text:
        return f"Location: {location_text}"
    return None


def extract_preferred_geography_quotes(text: str, plan: dict[str, Any]) -> dict[str, str | None]:
    location_filters = plan.get("location_filters") or {}
    preferred_regions = [normalize_text(value) for value in location_filters.get("employer_regions_preferred") or []]
    preferred_countries = [normalize_text(value) for value in location_filters.get("employer_presence_countries_preferred") or []]

    region_quote = None
    if any(value in {"european union", "eu", "europe"} for value in preferred_regions):
        region_quote = first_matching_line(text, EU_REGION_PATTERNS)

    country_quote = None
    if "spain" in preferred_countries:
        country_quote = first_matching_line(text, SPAIN_PRESENCE_PATTERNS)
    elif preferred_countries:
        country_quote = first_matching_line(text, preferred_countries)

    return {
        "region_quote": region_quote,
        "country_quote": country_quote,
    }


def same_host(url_a: str, url_b: str) -> bool:
    return urllib.parse.urlparse(url_a).netloc.lower() == urllib.parse.urlparse(url_b).netloc.lower()


def fetch_page(url: str) -> dict[str, Any]:
    html, _ = http_get(url)
    return {
        "url": url,
        "html": html,
        "text": html_to_text(html),
        "anchors": collect_anchors(html, url),
        "mailtos": collect_mailtos(html),
    }


def collect_followup_urls(candidate: dict[str, Any], primary_page: dict[str, Any]) -> list[str]:
    urls = list(candidate.get("contact_page_urls") or []) + list(candidate.get("people_page_urls") or [])
    for anchor in primary_page.get("anchors", []):
        href = anchor["href"]
        if not same_host(primary_page["url"], href):
            continue
        combined = normalize_text(" ".join([anchor["text"], href]))
        if any(token in combined for token in PAGE_HINT_TOKENS):
            urls.append(href)
    return unique_preserve_order(urls)


def build_evidence_bundle(candidate: dict[str, Any], max_extra_pages: int = 3) -> dict[str, Any]:
    primary_url = candidate.get("detail_url") or candidate.get("company_url") or candidate.get("discovery_url")
    if not primary_url:
        return {"pages": [], "text": "", "contacts": [], "evidence_urls": []}

    pages: list[dict[str, Any]] = []
    try:
        primary_page = fetch_page(primary_url)
    except urllib.error.URLError:
        primary_page = {"url": primary_url, "html": "", "text": "", "anchors": [], "mailtos": []}
    pages.append(primary_page)

    for url in collect_followup_urls(candidate, primary_page):
        if len(pages) >= max_extra_pages + 1:
            break
        if url == primary_url:
            continue
        try:
            pages.append(fetch_page(url))
        except urllib.error.URLError:
            continue

    contacts = unique_contacts(extract_named_people(pages, candidate) + extract_public_channels(pages))
    evidence_urls = unique_preserve_order(
        [value for value in [candidate.get("discovery_url"), candidate.get("detail_url"), candidate.get("company_url")] if value]
        + [page["url"] for page in pages if page.get("url")]
    )
    return {
        "pages": pages,
        "text": "\n".join(page["text"] for page in pages if page.get("text")),
        "contacts": contacts,
        "evidence_urls": evidence_urls,
    }


def extract_public_channels(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        for email in page.get("mailtos", []):
            normalized = normalize_text(email)
            if normalized in seen:
                continue
            seen.add(normalized)
            confidence = "high" if any(token in normalized for token in ["jobs@", "careers@", "hiring@", "talent@"]) else "medium"
            channels.append(
                {
                    "contact_type": "channel",
                    "name_or_channel": email,
                    "role": None,
                    "contact_url_or_email": email,
                    "confidence": confidence,
                    "selection_reason": "Verified public email channel found on the company site.",
                    "evidence_urls": [page["url"]],
                    "allowed": True,
                }
            )
        for anchor in page.get("anchors", []):
            combined = normalize_text(" ".join([anchor["text"], anchor["href"]]))
            if not any(token in combined for token in ["contact", "careers", "jobs", "apply", "hiring"]):
                continue
            if anchor["href"] in seen:
                continue
            seen.add(anchor["href"])
            channels.append(
                {
                    "contact_type": "channel",
                    "name_or_channel": anchor["text"] or "Public contact page",
                    "role": None,
                    "contact_url_or_email": anchor["href"],
                    "confidence": "medium",
                    "selection_reason": "Verified public careers or contact page found on the company site.",
                    "evidence_urls": [page["url"], anchor["href"]],
                    "allowed": True,
                }
            )
    return channels


PERSON_ROLE_PATTERNS = [
    re.compile(r"^(?P<name>[A-Z][A-Za-zÀ-ÿ' .-]{2,80})\s+[—-]\s+(?P<role>[A-Z][A-Za-z/&(), .-]{2,120})$"),
    re.compile(r"^(?P<role>[A-Z][A-Za-z/&(), .-]{2,120}):\s*(?P<name>[A-Z][A-Za-zÀ-ÿ' .-]{2,80})$"),
]


def build_function_terms(plan: dict[str, Any]) -> list[str]:
    raw_terms = list(plan.get("target_role_families", [])) + list(plan.get("focus_topics", []))
    expanded: list[str] = []
    for term in raw_terms:
        normalized = normalize_text(term)
        if normalized:
            expanded.append(normalized)
        for token in re.split(r"[^a-z0-9]+", normalized):
            if len(token) >= 3 and token not in STOPWORDS:
                expanded.append(token)
    return unique_preserve_order(expanded)


def supports_founder_contact(company_text: str) -> bool:
    return first_matching_line(company_text, FOUNDER_ELIGIBILITY_PATTERNS) is not None


def classify_contact_type(role: str, plan: dict[str, Any], company_text: str) -> tuple[str, bool]:
    normalized_role = normalize_text(role)
    if any(token in normalized_role for token in RECRUITING_PATTERNS):
        return "recruiting", True

    function_terms = build_function_terms(plan)
    function_match = any(term in normalized_role for term in function_terms)
    lead_match = any(token in normalized_role for token in LEAD_PATTERNS)
    founder_match = any(token in normalized_role for token in FOUNDER_PATTERNS)

    if function_match and lead_match:
        return "functional_lead", True
    if function_match:
        return "similar_role", True
    if founder_match:
        return "founder", supports_founder_contact(company_text)
    return "other", False


def extract_named_people(pages: list[dict[str, Any]], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    company_text = "\n".join(page.get("text", "") for page in pages)
    contacts: list[dict[str, Any]] = []
    plan = candidate["plan"]
    for page in pages:
        for line in split_text_units(page.get("text", "")):
            for pattern in PERSON_ROLE_PATTERNS:
                match = pattern.match(line)
                if not match:
                    continue
                name = match.group("name").strip()
                role = match.group("role").strip()
                if len(name.split()) < 2 or normalize_text(name) == normalize_text(str(candidate.get("company", ""))):
                    continue
                contact_type, allowed = classify_contact_type(role, plan, company_text)
                if contact_type == "other":
                    continue
                contacts.append(
                    {
                        "contact_type": contact_type,
                        "name_or_channel": name,
                        "role": role,
                        "contact_url_or_email": page["url"],
                        "confidence": "medium",
                        "selection_reason": f"Public team page lists {name} as {role}.",
                        "evidence_urls": [page["url"]],
                        "allowed": allowed,
                    }
                )
    return contacts


def unique_contacts(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for contact in contacts:
        key = stable_json_hash(
            [
                contact.get("contact_type"),
                contact.get("name_or_channel"),
                contact.get("role"),
                contact.get("contact_url_or_email"),
            ]
        )
        if key not in by_key:
            by_key[key] = contact
    return list(by_key.values())


def contact_priority(contact_type: str) -> int:
    return {
        "recruiting": 5,
        "functional_lead": 4,
        "similar_role": 3,
        "founder": 2,
        "channel": 1,
    }.get(contact_type, 0)


def confidence_rank(confidence: str | None) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get((confidence or "").lower(), 0)


def detect_contact_channel(contact: dict[str, Any]) -> str:
    value = str(contact.get("contact_url_or_email") or "").strip().lower()
    if not value:
        return "other"
    if "@" in value and not value.startswith(("http://", "https://")):
        return "email"
    host = urllib.parse.urlparse(value).netloc.lower()
    if "linkedin.com" in host:
        return "linkedin"
    if "x.com" in host or "twitter.com" in host:
        return "x"
    return "other"


def contact_channel_preference_rank(contact: dict[str, Any], preferred_channels: list[str]) -> int:
    channel = detect_contact_channel(contact)
    normalized_preferences = [normalize_text(value) for value in preferred_channels if value]
    if channel in normalized_preferences:
        return len(normalized_preferences) - normalized_preferences.index(channel)
    if channel == "email":
        return 1
    return 0


def effective_contact_rank(contact: dict[str, Any], preferred_channels: list[str]) -> int:
    channel = detect_contact_channel(contact)
    base = contact_priority(str(contact.get("contact_type"))) * 10
    confidence = confidence_rank(str(contact.get("confidence")))
    channel_bonus = contact_channel_preference_rank(contact, preferred_channels) * 10
    channel_penalty = 2 if channel == "x" else 0
    return base + confidence + channel_bonus - channel_penalty


def select_best_contact(contacts: list[dict[str, Any]], preferred_channels: list[str] | None = None) -> dict[str, Any] | None:
    allowed = [contact for contact in contacts if contact.get("allowed")]
    if not allowed:
        return None
    preferred_channels = preferred_channels or []
    allowed.sort(
        key=lambda contact: (
            -effective_contact_rank(contact, preferred_channels),
            -contact_priority(str(contact.get("contact_type"))),
            contact.get("name_or_channel", ""),
        )
    )
    return allowed[0]


def best_matching_role_family(text: str, plan: dict[str, Any]) -> str:
    role_families = plan.get("target_role_families") or []
    if not role_families:
        return "Generalist"
    normalized_text = normalize_text(text)
    best_role = role_families[0]
    best_score = -1
    for role in role_families:
        score = 0
        normalized_role = normalize_text(role)
        if normalized_role and normalized_role in normalized_text:
            score += 3
        for token in re.split(r"[^a-z0-9]+", normalized_role):
            if len(token) < 3 or token in STOPWORDS:
                continue
            if token in normalized_text:
                score += 1
        if score > best_score:
            best_score = score
            best_role = role
    return best_role


def score_company_potential(source_kind: str, text: str) -> tuple[int, str | None]:
    score = {
        "leaderboard": 4,
        "funding_roundup": 4,
        "company_directory": 3,
        "company_html": 2,
        "public_people": 2,
        "linkedin_company": 1,
    }.get(source_kind, 1)
    growth_quote = first_matching_line(text, GROWTH_PATTERNS)
    product_quote = first_matching_line(text, PRODUCT_PATTERNS)
    team_quote = first_matching_line(text, TEAM_PATTERNS)
    if growth_quote:
        score += 1
    if product_quote:
        score += 1
    if team_quote:
        score += 1
    return min(score, 5), growth_quote or product_quote or team_quote


def score_role_plausibility(text: str, plan: dict[str, Any], source_kind: str) -> tuple[int, str | None]:
    normalized_text = normalize_text(text)
    for role in plan.get("target_role_families") or []:
        normalized_role = normalize_text(role)
        if normalized_role and normalized_role in normalized_text:
            quote = first_matching_line(text, [role]) or first_matching_line(text, [normalized_role])
            return 5, quote or role

    function_terms = build_function_terms(plan)
    function_quote = first_matching_line(text, function_terms)
    team_quote = first_matching_line(text, TEAM_PATTERNS)
    if function_quote and team_quote:
        return 4, function_quote
    if function_quote:
        return 3, function_quote
    if source_kind in {"leaderboard", "funding_roundup", "company_directory"} and team_quote:
        return 2, team_quote
    return 1 if team_quote else 0, team_quote


def evaluate_geography_filters(
    profile: dict[str, Any],
    *,
    detail_text: str,
    remote_quote: str | None,
    remote_state: str,
    geography_quote: str | None,
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
            normalized_detail = normalize_text(detail_text)
            if any(country in normalized_detail for country in hireable_from):
                geography_quote = geography_quote
            else:
                return "discarded", ["geography mismatch"]

    if reasons:
        return "pending", reasons
    return "new", []


def score_geography_fit(
    status: str,
    remote_quote: str | None,
    geography_quote: str | None,
    preferred_geography_quotes: dict[str, str | None] | None = None,
) -> int:
    if status == "discarded":
        return 0
    preferred_geography_quotes = preferred_geography_quotes or {}
    score = 1
    if remote_quote:
        score += 1
    if geography_quote:
        score += 1
    if preferred_geography_quotes.get("region_quote"):
        score += 1
    if preferred_geography_quotes.get("country_quote"):
        score += 1
    return min(score, 5)


def score_contactability(contact: dict[str, Any] | None) -> int:
    if contact is None:
        return 0
    base = {
        "recruiting": 5,
        "functional_lead": 4,
        "similar_role": 4,
        "founder": 3,
        "channel": 2,
    }.get(str(contact.get("contact_type")), 1)
    penalty = 0 if str(contact.get("confidence")).lower() != "low" else 1
    return max(1, base - penalty)


def score_evidence_quality(candidate: dict[str, Any], page_count: int, contact: dict[str, Any] | None) -> int:
    score = {"high": 3, "medium": 2, "low": 1}.get(str(candidate.get("source_confidence")), 1)
    if page_count > 1:
        score += 1
    if contact is not None:
        score += 1
    return min(score, 5)


def verification_confidence(candidate: dict[str, Any], page_count: int, status: str) -> str:
    if candidate.get("source_confidence") == "high" and page_count > 1 and status == "new":
        return "high"
    if candidate.get("source_confidence") == "low":
        return "low"
    return "medium"


def is_better_status(status: str) -> int:
    return {"new": 0, "pending": 1, "discarded": 2}.get(status, 9)


def is_better_prospect(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    return (
        is_better_status(candidate["status"]),
        -candidate["total_score"],
        -candidate["contactability_score"],
    ) < (
        is_better_status(existing["status"]),
        -existing["total_score"],
        -existing["contactability_score"],
    )


def verify_and_rank_candidates(
    candidates: list[dict[str, Any]],
    profile: dict[str, Any],
    plan: dict[str, Any],
    *,
    prospect_run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prospect_by_key: dict[str, dict[str, Any]] = {}
    contact_by_key: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        if candidate.get("discovery_error"):
            continue

        candidate = dict(candidate)
        candidate["plan"] = plan
        bundle = build_evidence_bundle(candidate)
        combined_text = bundle["text"] or candidate.get("raw_snippet", "")
        matched_role_family = best_matching_role_family(combined_text, plan)
        remote_quote, remote_state = extract_remote_evidence(combined_text, candidate.get("location_text"))
        geography_quote = extract_geography_evidence(combined_text, candidate.get("location_text"))
        preferred_geography_quotes = extract_preferred_geography_quotes(combined_text, plan)
        hireable_from = [
            country.lower()
            for country in (get_dotted(profile, "preferences.confirmed.search.geography.hireable_from") or [])
        ]
        if geography_quote and hireable_from and not any(country in geography_quote.lower() for country in hireable_from):
            geography_quote = first_matching_line(combined_text, hireable_from) or geography_quote
        status, reasons = evaluate_geography_filters(
            profile,
            detail_text=combined_text,
            remote_quote=remote_quote,
            remote_state=remote_state,
            geography_quote=geography_quote,
        )

        company_potential_score, company_quote = score_company_potential(candidate["source_kind"], combined_text)
        role_plausibility_score, role_quote = score_role_plausibility(combined_text, plan, candidate["source_kind"])
        preferred_channels = get_dotted(profile, "preferences.confirmed.prospecting.contacts.preferred_channels") or []
        selected_contact = select_best_contact(bundle["contacts"], preferred_channels)
        if selected_contact is None:
            reasons.append("contact channel missing")
            if status == "new":
                status = "pending"

        if company_potential_score < 2:
            status = "discarded"
            reasons = ["company potential too weak"]
        elif role_plausibility_score == 0:
            status = "discarded"
            reasons = ["role plausibility too weak"]

        geography_fit_score = score_geography_fit(
            status,
            remote_quote,
            geography_quote,
            preferred_geography_quotes,
        )
        contactability_score = score_contactability(selected_contact)
        evidence_quality_score = score_evidence_quality(candidate, len(bundle["pages"]), selected_contact)
        total_score = (
            company_potential_score * 3
            + role_plausibility_score * 3
            + geography_fit_score * 2
            + contactability_score * 2
            + evidence_quality_score
        )

        if status == "new" and role_plausibility_score <= 1:
            status = "pending"
            reasons.append("role signal weak")

        dedupe_key = career_shared.dedupe_company_role_key(candidate["company"], matched_role_family)
        prospect_row = {
            "dedupe_key": dedupe_key,
            "company": candidate["company"],
            "target_role_family": matched_role_family,
            "status": status,
            "rationale": "; ".join(
                value
                for value in [
                    company_quote,
                    role_quote,
                    preferred_geography_quotes.get("country_quote")
                    or preferred_geography_quotes.get("region_quote")
                    or geography_quote
                    or remote_quote,
                    selected_contact.get("selection_reason") if selected_contact else None,
                ]
                if value
            ),
            "company_potential_score": company_potential_score,
            "role_plausibility_score": role_plausibility_score,
            "geography_fit_score": geography_fit_score,
            "contactability_score": contactability_score,
            "evidence_quality_score": evidence_quality_score,
            "total_score": total_score,
            "company_potential_quote": company_quote,
            "role_plausibility_quote": role_quote,
            "geography_fit_quote": (
                preferred_geography_quotes.get("country_quote")
                or preferred_geography_quotes.get("region_quote")
                or geography_quote
                or remote_quote
            ),
            "contactability_quote": selected_contact.get("selection_reason") if selected_contact else None,
            "selected_contact_type": selected_contact.get("contact_type") if selected_contact else None,
            "selected_contact": selected_contact.get("name_or_channel") if selected_contact else None,
            "selected_contact_role": selected_contact.get("role") if selected_contact else None,
            "selected_contact_url_or_email": selected_contact.get("contact_url_or_email") if selected_contact else None,
            "contact_confidence": selected_contact.get("confidence") if selected_contact else None,
            "discovery_url": candidate.get("discovery_url"),
            "company_url": candidate.get("company_url") or candidate.get("detail_url") or candidate.get("discovery_url"),
            "source_kind": candidate.get("source_kind"),
            "source_record_id": candidate.get("source_record_id"),
            "evidence_urls": bundle["evidence_urls"],
            "first_seen_at": today_date(),
            "last_seen_at": today_date(),
            "prospect_run_id": prospect_run_id,
            "verification_confidence": verification_confidence(candidate, len(bundle["pages"]), status),
            "review_required": status == "pending",
            "review_reason": "; ".join(unique_preserve_order(reasons)) if reasons else None,
            "source_confidence": candidate.get("source_confidence"),
            "raw_snippet": candidate.get("raw_snippet"),
        }

        selected_contact_row = None
        if selected_contact is not None:
            selected_contact_row = {
                "contact_id": stable_json_hash(
                    [
                        dedupe_key,
                        selected_contact.get("name_or_channel"),
                        selected_contact.get("contact_url_or_email"),
                    ]
                )[:12],
                "prospect_dedupe_key": dedupe_key,
                "company": candidate["company"],
                "target_role_family": matched_role_family,
                "contact_type": selected_contact.get("contact_type"),
                "name_or_channel": selected_contact.get("name_or_channel"),
                "role": selected_contact.get("role"),
                "contact_url_or_email": selected_contact.get("contact_url_or_email"),
                "confidence": selected_contact.get("confidence"),
                "selection_reason": selected_contact.get("selection_reason"),
                "evidence_urls": selected_contact.get("evidence_urls"),
                "prospect_run_id": prospect_run_id,
                "selected": True,
            }

        existing = prospect_by_key.get(dedupe_key)
        if existing is None:
            prospect_by_key[dedupe_key] = prospect_row
            if selected_contact_row is not None:
                contact_by_key[dedupe_key] = selected_contact_row
            continue

        merged_urls = unique_preserve_order(existing.get("evidence_urls", []) + prospect_row["evidence_urls"])
        if is_better_prospect(prospect_row, existing):
            prospect_row["first_seen_at"] = existing.get("first_seen_at") or prospect_row["first_seen_at"]
            prospect_row["evidence_urls"] = merged_urls
            prospect_by_key[dedupe_key] = prospect_row
            if selected_contact_row is not None:
                contact_by_key[dedupe_key] = selected_contact_row
        else:
            existing["evidence_urls"] = merged_urls
            existing["last_seen_at"] = prospect_row["last_seen_at"]
            if selected_contact_row is not None and dedupe_key not in contact_by_key:
                contact_by_key[dedupe_key] = selected_contact_row

    prospects = list(prospect_by_key.values())
    prospects.sort(key=lambda row: (is_better_status(row["status"]), -row["total_score"], row["company"], row["target_role_family"]))
    contacts = [contact_by_key[row["dedupe_key"]] for row in prospects if row["dedupe_key"] in contact_by_key]
    return prospects, contacts
