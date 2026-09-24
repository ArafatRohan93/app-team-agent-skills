#!/usr/bin/env python3
"""Validate a theme spec before generating Dart from it.

Usage:
  python3 validate_theme_spec.py design/theme.spec.json [--allow-open-conflicts]

Exit code 0 = no errors (warnings may still need a human decision), 1 = errors.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theme_spec import SpecError, contrast_results, load_spec, validate  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="Path to theme.spec.json")
    ap.add_argument("--allow-open-conflicts", action="store_true",
                    help="Treat unresolved conflicts as warnings (for a provisional preview)")
    args = ap.parse_args()

    try:
        spec = load_spec(args.spec)
    except SpecError as e:
        sys.exit(f"error: {e}")

    errors, warnings = validate(spec, allow_open_conflicts=args.allow_open_conflicts)

    open_conflicts = [c for c in spec.get("conflicts") or [] if c.get("status", "open") == "open"]
    if open_conflicts:
        print("Conflicts that need a decision:")
        for c in open_conflicts:
            print(f"  - {c['target']}:")
            for cand in c.get("candidates", []):
                print(f"      {cand.get('value')}  ← {cand.get('source')}")
            if c.get("recommendation") is not None:
                print(f"      recommended: {c['recommendation']} — {c.get('reason', '')}")
        print()

    fails = [r for r in contrast_results(spec) if r["status"] == "fail"]
    if fails:
        print("Contrast below WCAG minimum (provided colours):")
        for r in fails:
            print(f"  - {r['mode']:5} {r['pair']:45} {r['ratio']:.2f}:1 (needs {r['min']}:1)")
        print()

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
