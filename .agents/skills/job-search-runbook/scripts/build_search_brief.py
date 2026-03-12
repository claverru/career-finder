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
    parser = argparse.ArgumentParser(description="Build the mini search brief from the canonical profile.")
    parser.add_argument("--profile", default=str(search_pipeline.DEFAULT_PROFILE_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = search_pipeline.read_yaml(Path(args.profile))
    brief = search_pipeline.build_search_brief(profile)
    print(json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True))
    if not brief["complete"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
