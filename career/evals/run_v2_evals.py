#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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


class V2EvalCases(unittest.TestCase):
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
            path = Path(tmp_dir) / "search_runs.jsonl"
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


if __name__ == "__main__":
    unittest.main()
