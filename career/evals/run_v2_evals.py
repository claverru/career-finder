#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


render_artifacts = load_module(
    ROOT / ".agents" / "skills" / "cv-optimize" / "scripts" / "render_artifacts.py",
    "render_artifacts_eval",
)
import_resume = load_module(
    ROOT / ".agents" / "skills" / "cv-optimize" / "scripts" / "import_resume.py",
    "import_resume_eval",
)
search_pipeline = load_module(
    ROOT / ".agents" / "skills" / "job-search-runbook" / "scripts" / "search_pipeline.py",
    "search_pipeline_eval",
)
prospect_pipeline = load_module(
    ROOT / ".agents" / "skills" / "company-prospecting-runbook" / "scripts" / "prospect_pipeline.py",
    "prospect_pipeline_eval",
)
sync_prospect_state = load_module(
    ROOT / ".agents" / "skills" / "company-prospecting-runbook" / "scripts" / "sync_prospect_state.py",
    "sync_prospect_state_eval",
)
sync_search_state = load_module(
    ROOT / ".agents" / "skills" / "job-search-runbook" / "scripts" / "sync_search_state.py",
    "sync_search_state_eval",
)


def build_fixture_http_get(mapping: dict[str, str]):
    def fake_http_get(url: str, accept: str = "text/html"):
        if url not in mapping:
            raise urllib.error.URLError(f"missing fixture for {url}")
        content = mapping[url]
        content_type = "application/json" if url.endswith(".json") else "text/html"
        return content, content_type

    return fake_http_get


class V2EvalCases(unittest.TestCase):
    def test_explicit_user_status_wins_over_free_form_note(self) -> None:
        entry = {
            "company": "Example Company",
            "role": "Senior Machine Learning Engineer",
            "batch_id": "20260316_9",
            "source_date": "20260316",
            "source_file": "search/batches/20260316_9.md",
            "user_note": "esperando respuesta del recruiter",
            "fields": {
                "final_company_apply_url": "https://example.com/apply",
                "user_status": "pending",
            },
        }

        record = sync_search_state.job_record_from_entry(entry)
        self.assertEqual(record["status"], "pending")

    def test_sync_search_state_preserves_existing_jobs_and_writes_compact_view(self) -> None:
        with tempfile.TemporaryDirectory(prefix="search_sync_eval_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            batches_dir = tmp_root / "batches"
            state_dir = tmp_root / "state"
            batches_dir.mkdir()
            state_dir.mkdir()

            existing_job = {
                "internal_job_id": "job_existing123",
                "dedupe_key": "example-company__senior-machine-learning-engineer",
                "company": "Example Company",
                "role": "Senior Machine Learning Engineer",
                "batch_id": "20260301_1",
                "source_batches": ["20260301_1"],
                "source_date": "20260301",
                "status": "applied",
                "discovery_url": None,
                "final_company_apply_url": "https://jobs.example.com/roles/123",
                "evidence_urls": [],
                "first_seen_at": "2026-03-01",
                "last_seen_at": "2026-03-01",
                "salary_band": "EUR80k-EUR95k base",
                "salary_basis": "Inferred",
                "salary_confidence": "Medium",
                "salary_evidence": "market proxy",
                "review_required": False,
                "review_reason": None,
                "user_note": "aplicado",
                "notes_history": [{"batch_id": "20260301_1", "note": "aplicado"}],
                "source_file": "search/batches/20260301_1.md",
            }
            sync_search_state.write_jsonl(state_dir / "jobs.jsonl", [existing_job])
            sync_search_state.write_jsonl(state_dir / "applications.jsonl", [])
            sync_search_state.write_jsonl(tmp_root / "memory_review.jsonl", [])

            original_batches = sync_search_state.BATCHES_DIR
            original_jobs = sync_search_state.JOBS_PATH
            original_applications = sync_search_state.APPLICATIONS_PATH
            original_reviews = sync_search_state.MEMORY_REVIEW_PATH
            original_compact = sync_search_state.COMPACT_JOBS_PATH
            try:
                sync_search_state.BATCHES_DIR = batches_dir
                sync_search_state.JOBS_PATH = state_dir / "jobs.jsonl"
                sync_search_state.APPLICATIONS_PATH = state_dir / "applications.jsonl"
                sync_search_state.MEMORY_REVIEW_PATH = tmp_root / "memory_review.jsonl"
                sync_search_state.COMPACT_JOBS_PATH = state_dir / "compact_jobs.md"
                counts = sync_search_state.sync()
            finally:
                sync_search_state.BATCHES_DIR = original_batches
                sync_search_state.JOBS_PATH = original_jobs
                sync_search_state.APPLICATIONS_PATH = original_applications
                sync_search_state.MEMORY_REVIEW_PATH = original_reviews
                sync_search_state.COMPACT_JOBS_PATH = original_compact

            jobs = sync_search_state.load_jsonl(state_dir / "jobs.jsonl")
            compact_text = (state_dir / "compact_jobs.md").read_text(encoding="utf-8")

        self.assertEqual(counts["jobs"], 1)
        self.assertEqual(jobs[0]["status"], "applied")
        self.assertEqual(jobs[0]["internal_job_id"], "job_existing123")
        self.assertIn("job_existing123", compact_text)
        self.assertIn("Senior Machine Learning Engineer", compact_text)

    def test_optional_projects_are_omitted(self) -> None:
        profile = render_artifacts.parse_cv_source(FIXTURES / "cv_no_projects.txt")
        latex = render_artifacts.render_latex(profile)
        self.assertEqual(profile["projects"], [])
        self.assertNotIn(r"\section*{Projects}", latex)

    def test_search_brief_finds_blockers(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_missing_brief.yaml").read_text(encoding="utf-8"))
        brief = search_pipeline.build_search_brief(profile)
        self.assertFalse(brief["complete"])
        blocker_paths = {item["path"] for item in brief["blocking_questions"]}
        self.assertIn("preferences.confirmed.search.remote_policy.mode", blocker_paths)
        self.assertIn("preferences.confirmed.search.geography.base", blocker_paths)

    def test_query_plan_generates_source_aware_queries(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        cv_text = (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8")
        plan = search_pipeline.derive_query_plan(cv_text, profile, bias="balanced")
        self.assertFalse(plan["is_partial"])
        self.assertEqual(plan["source_priority"][0], "greenhouse")
        self.assertTrue(any("site:boards.greenhouse.io" in query for query in plan["recommended_search_queries"]["structured_search"]))

    def test_greenhouse_normalization(self) -> None:
        raw_payload = (FIXTURES / "greenhouse_jobs.json").read_text(encoding="utf-8")
        original_http_get = search_pipeline.http_get
        try:
            search_pipeline.http_get = lambda url, accept="text/html": (raw_payload, "application/json")
            profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
            plan = search_pipeline.derive_query_plan(
                (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8"),
                profile,
                bias="balanced",
            )
            candidates = search_pipeline.discover_greenhouse(
                {"board_token": "examplecompany", "company": "Example Company"},
                plan,
            )
        finally:
            search_pipeline.http_get = original_http_get

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_kind"], "greenhouse")
        self.assertEqual(candidates[0]["source_record_id"], "12345")

    def test_verify_and_rank_extracts_evidence(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        candidate = {
            "source_kind": "greenhouse",
            "source_record_id": "12345",
            "company": "Example Company",
            "role": "Senior Machine Learning Engineer",
            "discovery_url": "https://job-boards.greenhouse.io/examplecompany/jobs/12345",
            "detail_url": "https://job-boards.greenhouse.io/examplecompany/jobs/12345",
            "raw_snippet": "Train and deploy recommender models in production.",
            "source_confidence": "high",
            "detail_text": (FIXTURES / "verified_role.txt").read_text(encoding="utf-8"),
        }
        ranked = search_pipeline.verify_and_rank_candidates([candidate], profile, search_run_id="run_test")
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["status"], "new")
        self.assertEqual(ranked[0]["salary_basis"], "Explicit")
        self.assertEqual(ranked[0]["source_kind"], "greenhouse")

    def test_remote_inference_accepts_flexible_workplace_in_spain(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        profile["preferences"]["confirmed"]["search"]["role_scope"]["require_production_ownership"] = False
        candidate = {
            "source_kind": "greenhouse",
            "source_record_id": "5676984004",
            "company": "Incode",
            "role": "Machine Learning Engineer",
            "discovery_url": "https://job-boards.greenhouse.io/incode/jobs/5676984004",
            "detail_url": "https://job-boards.greenhouse.io/incode/jobs/5676984004",
            "location_text": "Spain",
            "raw_snippet": "Deep learning computer vision role in Spain.",
            "source_confidence": "high",
            "detail_text": (
                "Full-time employee role. "
                "Benefits & Perks: Flexible Working Hours & Workplace. "
                "Develop and refine state-of-the-art deep learning models for computer vision applications. "
                "Design, build, and deploy the deep learning models that power our most advanced technologies."
            ),
        }
        ranked = search_pipeline.verify_and_rank_candidates([candidate], profile, search_run_id="run_test_remote")
        self.assertEqual(ranked[0]["status"], "new")
        self.assertIn("Flexible Working Hours", ranked[0]["remote_policy_quote"])
        self.assertIn("Spain", ranked[0]["spain_hiring_quote"])

    def test_modeling_only_role_passes_when_production_is_optional(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        profile["preferences"]["confirmed"]["search"]["role_scope"]["require_production_ownership"] = False
        candidate = {
            "source_kind": "greenhouse",
            "source_record_id": "999",
            "company": "Example Company",
            "role": "Senior Applied ML Engineer",
            "discovery_url": "https://job-boards.greenhouse.io/examplecompany/jobs/999",
            "detail_url": "https://job-boards.greenhouse.io/examplecompany/jobs/999",
            "location_text": "Remote (Spain)",
            "raw_snippet": "Train ranking models for ads.",
            "source_confidence": "high",
            "detail_text": (
                "Remote (Spain). Full-time employee role. "
                "Design, train, evaluate, and optimize ranking models for ads and recommender systems."
            ),
        }
        ranked = search_pipeline.verify_and_rank_candidates([candidate], profile, search_run_id="run_test_model")
        self.assertEqual(ranked[0]["status"], "new")

    def test_ops_only_role_is_rejected_when_modeling_is_required(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        profile["preferences"]["confirmed"]["search"]["role_scope"]["require_production_ownership"] = False
        candidate = {
            "source_kind": "greenhouse",
            "source_record_id": "1000",
            "company": "OpsCo",
            "role": "Senior MLOps Platform Engineer",
            "discovery_url": "https://job-boards.greenhouse.io/opsco/jobs/1000",
            "detail_url": "https://job-boards.greenhouse.io/opsco/jobs/1000",
            "location_text": "Remote (Spain)",
            "raw_snippet": "Own the inference platform.",
            "source_confidence": "high",
            "detail_text": (
                "Remote (Spain). Full-time employee role. "
                "Own our MLOps platform, serving infrastructure, monitoring, and deployment tooling for model inference."
            ),
        }
        ranked = search_pipeline.verify_and_rank_candidates([candidate], profile, search_run_id="run_test_ops")
        self.assertEqual(ranked[0]["status"], "discarded")

    def test_import_review_marks_ocr_low_confidence(self) -> None:
        report = import_resume.build_review_row(
            input_path=Path("/tmp/example.png"),
            extraction_method="ocr_image",
            confidence="low",
            review_required=True,
            extracted_text="Candidate Name\nProjects\nImage-derived content\n",
            notes=["OCR fallback was used"],
        )
        self.assertEqual(report["confidence"], "low")
        self.assertTrue(report["review_required"])
        self.assertIn("PROJECTS", report["detected_sections"])

    def test_reuse_window_detects_matching_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="search_runs_eval_") as tmp_dir:
            path = Path(tmp_dir) / "runs.jsonl"
            row = {
                "recorded_at": search_pipeline.utc_now(),
                "search_run_id": "run_existing",
                "plan_id": "plan123",
                "seed_fingerprint": "seed123",
            }
            search_pipeline.append_jsonl(path, row)
            reused = search_pipeline.maybe_reuse_existing_run("plan123", "seed123", path)
        self.assertIsNotNone(reused)
        self.assertEqual(reused["search_run_id"], "run_existing")

    def test_prospecting_keeps_company_without_vacancy_and_prefers_recruiter(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        cv_text = (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8")
        plan = prospect_pipeline.derive_prospect_plan(cv_text, profile, themes=["AI"])
        mapping = {
            "https://sifted.eu/leaderboards/sifted-250-2025": (FIXTURES / "prospect_leaderboard.html").read_text(encoding="utf-8"),
            "https://novaai.example/company": (FIXTURES / "prospect_novaai_company.html").read_text(encoding="utf-8"),
            "https://novaai.example/team": (FIXTURES / "prospect_novaai_team.html").read_text(encoding="utf-8"),
            "https://steadyops.example": (FIXTURES / "prospect_steadyops_company.html").read_text(encoding="utf-8"),
            "https://steadyops.example/contact": (FIXTURES / "prospect_steadyops_contact.html").read_text(encoding="utf-8"),
        }
        original_http_get = prospect_pipeline.http_get
        try:
            prospect_pipeline.http_get = build_fixture_http_get(mapping)
            candidates, _ = prospect_pipeline.discover_candidates(
                plan,
                seed_urls=["https://sifted.eu/leaderboards/sifted-250-2025"],
            )
            prospects, contacts = prospect_pipeline.verify_and_rank_candidates(
                candidates,
                profile,
                plan,
                prospect_run_id="run_prospect",
            )
        finally:
            prospect_pipeline.http_get = original_http_get

        self.assertGreaterEqual(len(prospects), 2)
        novaai = next(row for row in prospects if row["company"] == "NovaAI")
        self.assertEqual(novaai["status"], "new")
        self.assertEqual(novaai["selected_contact_type"], "recruiting")
        self.assertEqual(novaai["selected_contact"], "Jane Recruiter")
        self.assertTrue(any(row["company"] == "NovaAI" for row in contacts))

    def test_established_company_uses_public_channel_fallback(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        cv_text = (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8")
        plan = prospect_pipeline.derive_prospect_plan(cv_text, profile)
        mapping = {
            "https://steadyops.example": (FIXTURES / "prospect_steadyops_company.html").read_text(encoding="utf-8"),
            "https://steadyops.example/contact": (FIXTURES / "prospect_steadyops_contact.html").read_text(encoding="utf-8"),
        }
        original_http_get = prospect_pipeline.http_get
        try:
            prospect_pipeline.http_get = build_fixture_http_get(mapping)
            candidates = prospect_pipeline.discover_company_html({"company": "SteadyOps", "company_url": "https://steadyops.example"}, plan)
            prospects, _ = prospect_pipeline.verify_and_rank_candidates(
                candidates,
                profile,
                plan,
                prospect_run_id="run_steady",
            )
        finally:
            prospect_pipeline.http_get = original_http_get

        self.assertEqual(len(prospects), 1)
        steady = prospects[0]
        self.assertEqual(steady["status"], "new")
        self.assertGreaterEqual(steady["company_potential_score"], 3)
        self.assertEqual(steady["selected_contact_type"], "channel")
        self.assertEqual(steady["selected_contact"], "jobs@steadyops.example")

    def test_marketing_user_can_match_without_published_marketing_role(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_marketing.yaml").read_text(encoding="utf-8"))
        cv_text = (FIXTURES / "cv_marketing.txt").read_text(encoding="utf-8")
        plan = prospect_pipeline.derive_prospect_plan(cv_text, profile)
        mapping = {
            "https://growthbox.example": (FIXTURES / "prospect_marketing_company.html").read_text(encoding="utf-8"),
            "https://growthbox.example/team": (FIXTURES / "prospect_marketing_team.html").read_text(encoding="utf-8"),
        }
        original_http_get = prospect_pipeline.http_get
        try:
            prospect_pipeline.http_get = build_fixture_http_get(mapping)
            candidates = prospect_pipeline.discover_company_html({"company": "GrowthBox", "company_url": "https://growthbox.example"}, plan)
            prospects, _ = prospect_pipeline.verify_and_rank_candidates(
                candidates,
                profile,
                plan,
                prospect_run_id="run_growthbox",
            )
        finally:
            prospect_pipeline.http_get = original_http_get

        self.assertEqual(len(prospects), 1)
        growthbox = prospects[0]
        self.assertEqual(growthbox["status"], "new")
        self.assertEqual(growthbox["target_role_family"], "Growth Marketing Manager")
        self.assertEqual(growthbox["selected_contact_type"], "functional_lead")

    def test_prospecting_respects_geography_hard_filter(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        cv_text = (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8")
        plan = prospect_pipeline.derive_prospect_plan(cv_text, profile, themes=["AI"])
        mapping = {
            "https://usonlyai.example": (FIXTURES / "prospect_us_only_company.html").read_text(encoding="utf-8"),
        }
        original_http_get = prospect_pipeline.http_get
        try:
            prospect_pipeline.http_get = build_fixture_http_get(mapping)
            candidates = prospect_pipeline.discover_company_html({"company": "USOnlyAI", "company_url": "https://usonlyai.example"}, plan)
            prospects, _ = prospect_pipeline.verify_and_rank_candidates(
                candidates,
                profile,
                plan,
                prospect_run_id="run_usonly",
            )
        finally:
            prospect_pipeline.http_get = original_http_get

        self.assertEqual(prospects[0]["status"], "discarded")

    def test_prospecting_prefers_eu_and_spain_presence_in_geography_score(self) -> None:
        profile = yaml.safe_load((FIXTURES / "profile_complete_brief.yaml").read_text(encoding="utf-8"))
        profile["preferences"]["confirmed"]["search"]["geography"]["employer_regions_preferred"] = ["European Union"]
        profile["preferences"]["confirmed"]["search"]["geography"]["employer_presence_countries_preferred"] = ["Spain"]
        cv_text = (FIXTURES / "cv_no_projects.txt").read_text(encoding="utf-8")
        plan = prospect_pipeline.derive_prospect_plan(cv_text, profile, themes=["AI"])
        mapping = {
            "https://steadyops.example": (FIXTURES / "prospect_steadyops_company.html").read_text(encoding="utf-8"),
            "https://steadyops.example/contact": (FIXTURES / "prospect_steadyops_contact.html").read_text(encoding="utf-8"),
            "https://bayremote.example": (FIXTURES / "prospect_us_remote_company.html").read_text(encoding="utf-8"),
        }
        original_http_get = prospect_pipeline.http_get
        try:
            prospect_pipeline.http_get = build_fixture_http_get(mapping)
            candidates = [
                *prospect_pipeline.discover_company_html({"company": "SteadyOps", "company_url": "https://steadyops.example"}, plan),
                *prospect_pipeline.discover_company_html({"company": "BayRemote", "company_url": "https://bayremote.example"}, plan),
            ]
            prospects, _ = prospect_pipeline.verify_and_rank_candidates(
                candidates,
                profile,
                plan,
                prospect_run_id="run_geo_pref",
            )
        finally:
            prospect_pipeline.http_get = original_http_get

        steady = next(row for row in prospects if row["company"] == "SteadyOps")
        bayremote = next(row for row in prospects if row["company"] == "BayRemote")
        self.assertGreater(steady["geography_fit_score"], bayremote["geography_fit_score"])
        self.assertGreater(steady["total_score"], bayremote["total_score"])
        self.assertIn("Spain", steady["geography_fit_quote"])

    def test_select_best_contact_prefers_email_and_linkedin_over_other_channels(self) -> None:
        preferred_channels = ["email", "linkedin"]
        email_contact = {
            "contact_type": "channel",
            "name_or_channel": "jobs@example.com",
            "role": None,
            "contact_url_or_email": "jobs@example.com",
            "confidence": "high",
            "allowed": True,
        }
        founder_x_contact = {
            "contact_type": "founder",
            "name_or_channel": "Founder Name",
            "role": "Co-founder & CEO",
            "contact_url_or_email": "https://x.com/founder",
            "confidence": "medium",
            "allowed": True,
        }
        founder_linkedin_contact = {
            "contact_type": "founder",
            "name_or_channel": "Founder Name",
            "role": "Co-founder & CEO",
            "contact_url_or_email": "https://www.linkedin.com/in/founder-name",
            "confidence": "medium",
            "allowed": True,
        }

        best_among_email_and_x = prospect_pipeline.select_best_contact(
            [founder_x_contact, email_contact],
            preferred_channels,
        )
        best_among_founders = prospect_pipeline.select_best_contact(
            [founder_x_contact, founder_linkedin_contact],
            preferred_channels,
        )

        self.assertEqual(best_among_email_and_x["contact_url_or_email"], "jobs@example.com")
        self.assertEqual(
            best_among_founders["contact_url_or_email"],
            "https://www.linkedin.com/in/founder-name",
        )

    def test_sync_prospect_state_dedupes_company_and_role_family(self) -> None:
        with tempfile.TemporaryDirectory(prefix="prospect_sync_eval_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            batches_dir = tmp_root / "batches"
            state_dir = tmp_root / "state"
            batches_dir.mkdir()
            state_dir.mkdir()
            (batches_dir / "20260313_1.md").write_text(
                "\n".join(
                    [
                        "P1) NovaAI",
                        "- Prospect status: new",
                        "- Target role family: Senior Machine Learning Engineer",
                        "- Total score: 24",
                        "- Selected contact type: recruiting",
                        "- Selected contact: Jane Recruiter",
                        "- Contact url or email: careers@novaai.example",
                        "- Contact confidence: high",
                        "- Evidence urls: https://novaai.example/company",
                    ]
                ),
                encoding="utf-8",
            )
            (batches_dir / "20260313_2.md").write_text(
                "\n".join(
                    [
                        "P1) NovaAI",
                        "- Prospect status: new",
                        "- Target role family: Senior Machine Learning Engineer",
                        "- Total score: 26",
                        "- Selected contact type: recruiting",
                        "- Selected contact: Jane Recruiter",
                        "- Contact url or email: careers@novaai.example",
                        "- Contact confidence: high",
                        "- Evidence urls: https://novaai.example/team",
                    ]
                ),
                encoding="utf-8",
            )

            original_batches = sync_prospect_state.BATCHES_DIR
            original_prospects = sync_prospect_state.PROSPECTS_PATH
            original_contacts = sync_prospect_state.CONTACTS_PATH
            try:
                sync_prospect_state.BATCHES_DIR = batches_dir
                sync_prospect_state.PROSPECTS_PATH = state_dir / "prospects.jsonl"
                sync_prospect_state.CONTACTS_PATH = state_dir / "contacts.jsonl"
                counts = sync_prospect_state.sync()
            finally:
                sync_prospect_state.BATCHES_DIR = original_batches
                sync_prospect_state.PROSPECTS_PATH = original_prospects
                sync_prospect_state.CONTACTS_PATH = original_contacts

            prospects = sync_prospect_state.load_jsonl(state_dir / "prospects.jsonl")
            contacts = sync_prospect_state.load_jsonl(state_dir / "contacts.jsonl")
        self.assertEqual(counts["prospects"], 1)
        self.assertEqual(len(prospects), 1)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(prospects[0]["dedupe_key"], "novaai__senior-machine-learning-engineer")


if __name__ == "__main__":
    unittest.main()
