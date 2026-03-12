#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import search_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a staged search plan from the canonical CV and preferences.")
    parser.add_argument("--profile", default=str(search_pipeline.DEFAULT_PROFILE_PATH))
    parser.add_argument("--cv", default=str(search_pipeline.DEFAULT_CV_PATH))
    parser.add_argument("--bias", choices=("precision_first", "balanced", "coverage_first"), default="balanced")
    parser.add_argument("--record", action="store_true", help="Append a planning-only run record to search_runs.jsonl.")
    parser.add_argument("--search-runs-path", default=str(search_pipeline.DEFAULT_SEARCH_RUNS_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = search_pipeline.read_yaml(Path(args.profile))
    cv_text = Path(args.cv).read_text(encoding="utf-8")
    plan = search_pipeline.derive_query_plan(cv_text, profile, bias=args.bias)

    if args.record:
        seed_fingerprint = search_pipeline.build_seed_fingerprint([], [])
        row = search_pipeline.build_search_run_row(
            plan=plan,
            seed_fingerprint=seed_fingerprint,
            sources_consulted=[],
            counts={"discovered": 0, "verified": 0, "kept": 0, "discarded": 0},
            status="planned_only",
            reasons=["plan recorded without discovery"],
        )
        search_pipeline.append_jsonl(Path(args.search_runs_path), row)
        plan["search_run_id"] = row["search_run_id"]

    print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    if plan["is_partial"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
