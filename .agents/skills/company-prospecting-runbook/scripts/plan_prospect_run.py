#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prospect_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a staged company-prospecting plan from the canonical CV and preferences.")
    parser.add_argument("--profile", default=str(prospect_pipeline.DEFAULT_PROFILE_PATH))
    parser.add_argument("--cv", default=str(prospect_pipeline.DEFAULT_CV_PATH))
    parser.add_argument("--theme", action="append", default=[])
    parser.add_argument("--target-role", action="append", default=[])
    parser.add_argument("--bias", choices=("precision_first", "balanced", "coverage_first"), default="balanced")
    parser.add_argument("--record", action="store_true", help="Append a planning-only run record to runs.jsonl.")
    parser.add_argument("--prospect-runs-path", default=str(prospect_pipeline.DEFAULT_PROSPECT_RUNS_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = prospect_pipeline.read_yaml(Path(args.profile))
    cv_text = Path(args.cv).read_text(encoding="utf-8")
    plan = prospect_pipeline.derive_prospect_plan(
        cv_text,
        profile,
        bias=args.bias,
        themes=args.theme,
        target_roles=args.target_role,
    )

    if args.record:
        seed_fingerprint = prospect_pipeline.build_seed_fingerprint([], [])
        row = prospect_pipeline.build_prospect_run_row(
            plan=plan,
            seed_fingerprint=seed_fingerprint,
            sources_consulted=[],
            counts={"discovered": 0, "verified": 0, "kept": 0, "discarded": 0},
            status="planned_only",
            reasons=["plan recorded without discovery"],
        )
        prospect_pipeline.append_jsonl(Path(args.prospect_runs_path), row)
        plan["prospect_run_id"] = row["prospect_run_id"]

    print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    if plan["is_partial"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
