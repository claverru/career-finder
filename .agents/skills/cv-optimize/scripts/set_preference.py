#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


CAREER_ROOT = Path(__file__).resolve().parents[4] / "career"
PROFILE_PATH = CAREER_ROOT / "profile" / "profile.yaml"
PROFILE_EXAMPLE_PATH = CAREER_ROOT / "profile" / "profile.example.yaml"
ALLOWED_PREFIXES = ("preferences.confirmed", "memory.confirmed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist a confirmed preference or confirmed memory path into profile.yaml.",
    )
    parser.add_argument(
        "path",
        help="Dotted path under preferences.confirmed or memory.confirmed.",
    )
    parser.add_argument(
        "value",
        help="YAML literal for the value to store. Quote strings with spaces.",
    )
    parser.add_argument(
        "--mode",
        choices=("set", "append"),
        default="set",
        help="Replace an existing value or append unique items to an existing list.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the intended change without writing profile.yaml.",
    )
    return parser.parse_args()


def ensure_allowed_path(path: str) -> None:
    if any(path == prefix or path.startswith(f"{prefix}.") for prefix in ALLOWED_PREFIXES):
        return
    allowed = ", ".join(ALLOWED_PREFIXES)
    raise ValueError(f"path must live under one of: {allowed}")


def read_profile() -> dict:
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"missing {PROFILE_PATH}. Seed it from {PROFILE_EXAMPLE_PATH} before persisting preferences."
        )
    with PROFILE_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_profile(profile: dict) -> None:
    rendered = yaml.safe_dump(
        profile,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )
    PROFILE_PATH.write_text(rendered, encoding="utf-8")


def resolve_target(profile: dict, dotted_path: str) -> tuple[dict, str]:
    parts = dotted_path.split(".")
    current = profile

    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"missing path segment: {part}")
        current = current[part]

    leaf = parts[-1]
    if not isinstance(current, dict) or leaf not in current:
        raise KeyError(f"missing final key: {leaf}")
    return current, leaf


def parse_value(raw_value: str) -> object:
    return yaml.safe_load(raw_value)


def yaml_inline(value: object) -> str:
    rendered = yaml.safe_dump(value, allow_unicode=True, sort_keys=False).strip()
    return rendered.removesuffix("\n...")


def append_unique(existing: list, new_value: object) -> tuple[list, bool]:
    additions = new_value if isinstance(new_value, list) else [new_value]
    updated = list(existing)
    changed = False

    for item in additions:
        if item not in updated:
            updated.append(item)
            changed = True

    return updated, changed


def main() -> None:
    try:
        args = parse_args()
        ensure_allowed_path(args.path)

        profile = read_profile()
        container, key = resolve_target(profile, args.path)
        current_value = container[key]
        new_value = parse_value(args.value)

        if args.mode == "append":
            if not isinstance(current_value, list):
                raise TypeError(f"{args.path} is not a list; use --mode set instead")
            updated_value, changed = append_unique(current_value, new_value)
        else:
            updated_value = new_value
            changed = updated_value != current_value

        print(f"path: {args.path}")
        print(f"mode: {args.mode}")
        print(f"old: {yaml_inline(current_value)}")
        print(f"new: {yaml_inline(updated_value)}")

        if not changed:
            print("result: no change")
            return

        if args.dry_run:
            print("result: dry run only; profile.yaml not written")
            return

        container[key] = updated_value
        write_profile(profile)
        print("result: profile.yaml updated")
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
