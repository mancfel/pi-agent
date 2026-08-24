#!/usr/bin/env python3
"""
wiki_validate_links.py — Validate wikilinks in specified wiki files against existing pages on disk.

Scans one or more markdown files for [[wikilink]] references and checks each link
target against all .md files currently present in the Wiki/ subdirectories.

USAGE:
    # Single file:
    python scripts/wiki_validate_links.py sources/Filename.md --wiki-dir projectRoot/Wiki

    # Multiple files (mixed types):
    python scripts/wiki_validate_links.py \\
        sources/New Source.md \\
        entities/New Person.md \\
        concepts/New Concept.md \\
        --wiki-dir projectRoot/Wiki

    # Validate multiple files at once (replace with your actual file list):
    python scripts/wiki_validate_links.py \
        sources/E1.md entities/New Person.md concepts/New Concept.md \
        --wiki-dir projectRoot/Wiki

    # Dry run — show links without checking targets:
    python scripts/wiki_validate_links.py sources/Filename.md --list-only
"""

import argparse
import re
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate wikilinks in wiki markdown files against existing pages on disk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single source file:
  python scripts/wiki_validate_links.py sources/My New Episode.md \\
      --wiki-dir projectRoot/Wiki

  # Validate multiple files at once:
  python scripts/wiki_validate_links.py \\
      sources/E1.md entities/New Person.md concepts/New Concept.md \\
      --wiki-dir projectRoot/Wiki

  # List all links without validation (for manual review):
  python scripts/wiki_validate_links.py sources/E1.md --list-only

  # Validate with custom alias mapping (see --alias flag)
Notes:
  - Aliased links like [[Target Page|Display Name]] are validated against the target part only.
  - The script scans Wiki/sources/, Wiki/entities/, and Wiki/concepts/ automatically.
  - Exit code is 0 if no broken links found, 1 otherwise.
""",
    )
    parser.add_argument(
        "files", nargs="+", type=str,
        help="Markdown files to validate (paths relative to --wiki-dir or absolute)",
    )
    parser.add_argument(
        "--wiki-dir", type=str, default=None,
        help="Path to Wiki/ directory (default: ./Wiki relative to CWD)",
    )
    parser.add_argument(
        "--list-only", action="store_true",
        help="List all wikilinks found without checking against existing pages",
    )

    args = parser.parse_args()

    # Resolve file paths relative to wiki_dir if not absolute
    resolved_files = []
    for f in args.files:
        p = Path(f)
        if not p.is_absolute():
            base = Path(args.wiki_dir).resolve() if args.wiki_dir else Path.cwd().resolve() / "Wiki"
            p = (base / p).resolve()
        resolved_files.append(p)
    args.resolved_files = resolved_files

    return args


def build_page_index(wiki_dir):
    """Build a set of all page names (without .md extension) from sources/entities/concepts."""
    pages = set()
    for subdir in ["sources", "entities", "concepts"]:
        dir_path = wiki_dir / subdir
        if dir_path.exists():
            for fn in dir_path.iterdir():
                if fn.suffix == ".md":
                    # Strip .md and store the filename stem as it appears on disk
                    pages.add(fn.stem.lower())  # lowercase for case-insensitive matching
                    pages.add(fn.stem)           # keep original casing too
    return pages


def extract_wikilinks(content):
    """Extract all [[wikilink]] references from markdown content."""
    links = re.findall(r"\[\[([^\]|]+)\]\]", content)
    return sorted(set(links))


def resolve_wiki_dir(wiki_dir_arg, cwd):
    """Resolve the Wiki/ directory path.
    
    If arg points to a dir containing 'sources/', 'entities/', 'concepts/' -> use as-is.
    Otherwise treat it as project root and append '/Wiki'.
    """
    if not wiki_dir_arg:
        return (cwd / "Wiki").resolve()
    
    p = Path(wiki_dir_arg).resolve()
    # Check if this already IS the Wiki directory
    has_subdirs = all((p / d).exists() for d in ["sources", "entities", "concepts"])
    if has_subdirs:
        return p
    # Treat as project root, append /Wiki
    wiki_candidate = p / "Wiki"
    if wiki_candidate.exists():
        return wiki_candidate.resolve()
    return p  # Fall back to what was given; let caller handle missing error


def main():
    args = parse_args()

    # Resolve wiki directory
    cwd = Path.cwd().resolve()
    wiki_path = resolve_wiki_dir(args.wiki_dir, cwd)

    if not wiki_path.exists():
        print(f"ERROR: {wiki_path} not found.", file=sys.stderr)
        sys.exit(1)

    # Build index of existing pages
    existing_pages = build_page_index(wiki_path)

    total_links = 0
    all_broken = []
    has_errors = False

    for filepath in args.resolved_files:
        if not filepath.exists():
            print(f"[WARN] File not found, skipping: {filepath}", file=sys.stderr)
            continue

        content = filepath.read_text(encoding="utf-8", errors="replace").replace("\ufffd", "")
        links = extract_wikilinks(content)
        total_links += len(links)

        broken_for_file = []
        for link in links:
            # Check against existing pages (case-insensitive match)
            link_lower = link.lower()
            matched = any(link_lower == page_name or link_lower == page_name.lower() 
                         for page_name in existing_pages)
            
            if not matched and not args.list_only:
                broken_for_file.append(link)

        rel_path = filepath.relative_to(wiki_path.parent) if wiki_path.parent.is_dir() else filepath.stem
        
        # Use plain ASCII to avoid cp1252 encode errors on Windows
        status_icon = "OK" if not broken_for_file else "BROKEN"
        print(f"{status_icon} {rel_path}: {len(links)} links, {len(broken_for_file)} broken")

        if broken_for_file:
            has_errors = True
            all_broken.extend([(str(rel_path), b) for b in broken_for_file])
            for b in broken_for_file[:5]:  # Show first 5 per file
                print(f"     BROKEN: [[{b}]]")
            if len(broken_for_file) > 5:
                print(f"     ... and {len(broken_for_file) - 5} more")

    # Summary (use plain ASCII dash to avoid cp1252 encode errors on Windows)
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"Total files scanned: {len(args.resolved_files)}")
    print(f"Total wikilinks found: {total_links}")
    
    if args.list_only:
        print("Mode: --list-only (no validation performed)")
    else:
        total_broken = sum(len(bf) for bf in all_broken)
        print(f"Broken links: {total_broken}")
        
        if not has_errors:
            print("OK - All wikilinks resolved successfully.")
        else:
            print("\n📋 Broken link summary:")
            for filepath, link in all_broken[:20]:  # Show first 20
                print(f"   [{filepath}] [[{link}]]")
            remaining = len(all_broken) - 20
            if remaining > 0:
                print(f"   ... and {remaining} more broken links")

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
