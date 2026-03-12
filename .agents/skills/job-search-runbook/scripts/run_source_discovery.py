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
    parser = argparse.ArgumentParser(description="Run discovery adapters against configured sources and seed URLs.")
    parser.add_argument("--plan-json", required=True, help="Path to a query plan JSON file.")
    parser.add_argument("--source-catalog", default=str(search_pipeline.DEFAULT_SOURCE_CATALOG_PATH))
    parser.add_argument("--seed-url", action="append", default=[], help="Additional seed URLs to normalize and fetch.")
    parser.add_argument("--output", default=str(search_pipeline.DEFAULT_DISCOVERY_OUTPUT_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    source_catalog = search_pipeline.load_source_catalog(Path(args.source_catalog))
    candidates, consulted_sources = search_pipeline.discover_candidates(
        plan,
        source_catalog=source_catalog,
        seed_urls=args.seed_url,
    )
    search_pipeline.write_jsonl(Path(args.output), candidates)
    print(json.dumps({"consulted_sources": consulted_sources, "candidate_count": len(candidates)}, indent=2))


if __name__ == "__main__":
    main()
