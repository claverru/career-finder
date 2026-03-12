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
    parser = argparse.ArgumentParser(description="Run the staged job-search pipeline end to end.")
    parser.add_argument("--profile", default=str(search_pipeline.DEFAULT_PROFILE_PATH))
    parser.add_argument("--cv", default=str(search_pipeline.DEFAULT_CV_PATH))
    parser.add_argument("--source-catalog", default=str(search_pipeline.DEFAULT_SOURCE_CATALOG_PATH))
    parser.add_argument("--seed-url", action="append", default=[])
    parser.add_argument("--bias", choices=("precision_first", "balanced", "coverage_first"), default="balanced")
    parser.add_argument("--search-runs-path", default=str(search_pipeline.DEFAULT_SEARCH_RUNS_PATH))
    parser.add_argument("--discovery-output", default=str(search_pipeline.DEFAULT_DISCOVERY_OUTPUT_PATH))
    parser.add_argument("--ranked-output", default=str(search_pipeline.DEFAULT_RANKED_OUTPUT_PATH))
    parser.add_argument("--force", action="store_true", help="Ignore recent matching runs and execute discovery anyway.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile_path = Path(args.profile)
    cv_path = Path(args.cv)
    search_runs_path = Path(args.search_runs_path)
    source_catalog = search_pipeline.load_source_catalog(Path(args.source_catalog))
    profile = search_pipeline.read_yaml(profile_path)
    plan = search_pipeline.derive_query_plan(cv_path.read_text(encoding="utf-8"), profile, bias=args.bias)

    if plan["is_partial"]:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(3)

    seed_fingerprint = search_pipeline.build_seed_fingerprint(source_catalog, args.seed_url)
    reused = None if args.force else search_pipeline.maybe_reuse_existing_run(plan["plan_id"], seed_fingerprint, search_runs_path)
    if reused is not None:
        row = search_pipeline.build_search_run_row(
            plan=plan,
            seed_fingerprint=seed_fingerprint,
            sources_consulted=reused.get("sources_consulted", []),
            counts=reused.get("counts", {}),
            status="reused_existing_plan",
            reasons=["matching search plan and source inputs found inside the reuse window"],
            reused_run_id=reused.get("search_run_id"),
        )
        search_pipeline.append_jsonl(search_runs_path, row)
        print(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True))
        return

    candidates, consulted_sources = search_pipeline.discover_candidates(
        plan,
        source_catalog=source_catalog,
        seed_urls=args.seed_url,
    )
    search_pipeline.write_jsonl(Path(args.discovery_output), candidates)

    draft_run = search_pipeline.build_search_run_row(
        plan=plan,
        seed_fingerprint=seed_fingerprint,
        sources_consulted=consulted_sources,
        counts={"discovered": len(candidates), "verified": 0, "kept": 0, "discarded": 0},
        status="discovered",
        reasons=[],
    )
    ranked = search_pipeline.verify_and_rank_candidates(candidates, profile, search_run_id=draft_run["search_run_id"])
    search_pipeline.write_jsonl(Path(args.ranked_output), ranked)

    final_row = dict(draft_run)
    final_row["counts"] = {
        "discovered": len(candidates),
        "verified": len(ranked),
        "kept": sum(1 for row in ranked if row["status"] == "new"),
        "discarded": sum(1 for row in ranked if row["status"] == "discarded"),
        "pending": sum(1 for row in ranked if row["status"] == "pending"),
    }
    final_row["status"] = "completed"
    search_pipeline.append_jsonl(search_runs_path, final_row)
    print(json.dumps(final_row, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
