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
    parser = argparse.ArgumentParser(description="Verify discovered candidates and rank them against confirmed preferences.")
    parser.add_argument("--profile", default=str(search_pipeline.DEFAULT_PROFILE_PATH))
    parser.add_argument("--candidates-jsonl", default=str(search_pipeline.DEFAULT_DISCOVERY_OUTPUT_PATH))
    parser.add_argument("--search-run-id", required=True)
    parser.add_argument("--output", default=str(search_pipeline.DEFAULT_RANKED_OUTPUT_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = search_pipeline.read_yaml(Path(args.profile))
    candidates = search_pipeline.load_jsonl(Path(args.candidates_jsonl))
    ranked = search_pipeline.verify_and_rank_candidates(candidates, profile, search_run_id=args.search_run_id)
    search_pipeline.write_jsonl(Path(args.output), ranked)
    summary = {
        "verified": len(ranked),
        "kept": sum(1 for row in ranked if row["status"] == "new"),
        "pending": sum(1 for row in ranked if row["status"] == "pending"),
        "discarded": sum(1 for row in ranked if row["status"] == "discarded"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
