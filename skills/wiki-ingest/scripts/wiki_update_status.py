#!/usr/bin/env python3
"""
wiki_update_status.py — Batch update source statuses in Wiki/index.md

Updates one or more sources from 'Unprocessed' to 'Processed - YYYY-MM-DD'
by matching exact line strings and replacing them.

USAGE:
    python scripts/wiki_update_status.py --help
    python scripts/wiki_update_status.py \
        --old "| 35 | [Old Title](path/file.txt) | FOLDER | Unprocessed |" \
        --new "| 35 | [New Cleaned Title](path/file.txt) | FOLDER | Processed - 2025-08-19 |" \
        --wiki-dir projectRoot/Wiki

For multiple updates, repeat --old/--new pairs (up to 50 at a time):
    python scripts/wiki_update_status.py \
        --old "| 35 | ... | Unprocessed |" --new "| 35 | ... | Processed - 2025-08-19 |" \
        --old "| 36 | ... | Unprocessed |" --new "| 36 | ... | Processed - 2025-08-19 |" \
        --wiki-dir projectRoot/Wiki
"""

import argparse
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch update source statuses in Wiki/index.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single source update:
  python scripts/wiki_update_status.py \\
      --old '| 35 | [Old Title](path/file.txt) | FOLDER | Unprocessed |' \\
      --new '| 35 | [New Cleaned Title](path/file.txt) | FOLDER | Processed - 2025-08-19 |'

  # Multiple sources (repeat --old/--new pairs):
  python scripts/wiki_update_status.py \\
      --old '| 35 | ... | Unprocessed |' --new '| 35 | ... | Processed - 2025-08-19 |' \\
      --old '| 36 | ... | Unprocessed |' --new '| 36 | ... | Processed - 2025-08-19 |' \\
      --old '| 37 | ... | Unprocessed |' --new '| 37 | ... | Processed - 2025-08-19 |'

  # Only show what would change (dry run):
  python scripts/wiki_update_status.py \\
      --old '| 35 | ... | Unprocessed |' --new '| 35 | ... | Processed - 2025-08-19 |' \\
      --dry-run

Note: The --wiki-dir argument is optional if you run from the Wiki/ directory.
""",
    )
    parser.add_argument(
        "--old", action="append", dest="updates_old",
        help="Exact line string to find in index.md (repeat for multiple updates)",
    )
    parser.add_argument(
        "--new", action="append", dest="updates_new",
        help="Replacement line string (one per --old, repeat in same order)",
    )
    parser.add_argument(
        "--wiki-dir", type=str, default=None,
        help="Path to Wiki/ directory (default: ./Wiki relative to CWD)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be changed without writing to disk",
    )

    args = parser.parse_args()

    if not args.updates_old or not args.updates_new:
        parser.error("You must provide at least one --old and one --new pair.")

    if len(args.updates_old) != len(args.updates_new):
        parser.error(f"--old ({len(args.updates_old)}) and --new ({len(args.updates_new)}) counts don't match.")

    return args


def main():
    args = parse_args()

    # Resolve wiki directory
    if args.wiki_dir:
        wiki_path = Path(args.wiki_dir).resolve()
    else:
        wiki_path = Path.cwd().resolve() / "Wiki"

    index_file = wiki_path / "index.md"
    if not index_file.exists():
        print(f"ERROR: {index_file} not found. Check --wiki-dir or run from Wiki/.", file=sys.stderr)
        sys.exit(1)

    # Read file with UTF-8 error handling
    raw_bytes = index_file.read_bytes()
    content = raw_bytes.decode("utf-8", errors="replace").replace("\ufffd", "")

    matched_count = 0
    skipped_lines = []

    for old, new in zip(args.updates_old, args.updates_new):
        if old in content:
            content = content.replace(old, new, 1)
            matched_count += 1
            print(f"[OK] Updated: {old[:70]}...")
        else:
            skipped_lines.append(old)
            print(f"[X] NOT FOUND (skipped): {old[:70]}...")

    # Write back only if changes were made
    if matched_count > 0:
        index_file.write_text(content, encoding="utf-8")
        remaining_unproc = content.count("Unprocessed")
        print(f"\n✅ Updated {matched_count} source(s). Remaining unprocessed: {remaining_unproc}")
    elif not args.dry_run:
        print("\n[WARN] No matches found. Nothing written to disk.")
        for s in skipped_lines:
            print(f"   Skipped: {s[:80]}")
    else:
        print("\n[Dry Run] Would have updated 0 sources (no exact matches found).")

    if skipped_lines and matched_count > 0:
        print(f"\n[WARN] Warning: {len(skipped_lines)} update(s) could not be applied due to line mismatch.")
        print("   Tip: Check the exact formatting of lines in index.md by grepping:")
        print(f'   grep "Unprocessed" {index_file}')


if __name__ == "__main__":
    main()
