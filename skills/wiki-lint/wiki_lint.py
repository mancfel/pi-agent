#!/usr/bin/env python3
"""Wiki Lint Tool — Integrity & Health Check for the Investment Wiki."""

import os
import re
import sys
from datetime import date


def find_wiki_root():
    """Auto-detect wiki root by checking multiple locations in priority order.

    Priority:
      1. Current working directory (if it contains Wiki/)
      2. Parent dirs from CWD looking for CLAUDE.md + Wiki/
      3. Walk up from script location looking for CLAUDE.md + Wiki/
      4. Environment variable WIKI_ROOT if set
    """
    # Check 1: current working directory
    cwd = os.getcwd()
    candidate_wiki = os.path.join(cwd, 'Wiki')
    if os.path.isdir(candidate_wiki) and os.path.isfile(os.path.join(cwd, 'CLAUDE.md')):
        return candidate_wiki

    # Check 2: walk up from CWD looking for project root (has both Wiki/ and CLAUDE.md)
    candidate = cwd
    while candidate != os.path.dirname(candidate):
        parent = os.path.dirname(candidate)
        wiki_candidate = os.path.join(parent, 'Wiki')
        if os.path.isdir(wiki_candidate) and os.path.isfile(os.path.join(parent, 'CLAUDE.md')):
            return wiki_candidate
        candidate = parent

    # Check 3: walk up from script location
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = skill_dir
    while candidate != os.path.dirname(candidate):
        if (os.path.isdir(os.path.join(candidate, 'Wiki')) and
                os.path.isfile(os.path.join(candidate, 'CLAUDE.md'))):
            return os.path.join(candidate, 'Wiki')
        candidate = os.path.dirname(candidate)

    # Check 4: environment variable
    env_root = os.environ.get('WIKI_ROOT')
    if env_root and os.path.isdir(env_root):
        return env_root

    print("WARNING: Could not auto-detect Wiki root. Use --wiki-root <path>")
    return None


def scan_wiki(wiki_root: str) -> dict:
    """Scan all wiki pages and return structured lint results."""
    if not os.path.isdir(wiki_root):
        print(f"ERROR: Wiki root not found at {wiki_root}")
        sys.exit(1)

    # Collect ALL wiki pages
    all_pages = {}
    for d in ['sources', 'entities', 'concepts']:
        dp = os.path.join(wiki_root, d)
        if not os.path.isdir(dp):
            continue
        for fn in sorted(os.listdir(dp)):
            fp = os.path.join(dp, fn)
            if fn.endswith('.md'):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        content = f.read()
                    all_pages[fn[:-3]] = {'path': fp, 'content': content}
                except Exception as e:
                    print(f"  WARNING: Could not read {fp}: {e}")

    existing_names = set(all_pages.keys())

    # Collect every non-aliased [[Name]] reference and where it comes from
    link_sources = {}
    for name, info in sorted(all_pages.items()):
        matches = re.findall(r'\[\[([^\]|]+)\]\]', info['content'])
        for m in matches:
            if m not in link_sources:
                link_sources[m] = []
            link_sources[m].append(name)

    broken_links = {l: sources for l, sources in link_sources.items()
                    if l not in existing_names}

    # Orphan Pages (no incoming links from ANY other page)
    inbound_links = set(link_sources.keys())
    orphans = [name for name in existing_names if name not in inbound_links]

    # Stale Pages - compare date_updated against newest source
    stale_pages = []
    latest_source_date = None
    for sname, sinfo in all_pages.items():
        smatch = re.search(r'date_updated:\s*(\d{4}-\d{2}-\d{2})', sinfo['content'])
        if smatch and (latest_source_date is None or smatch.group(1) > latest_source_date):
            latest_source_date = smatch.group(1)

    if latest_source_date:
        for name, info in all_pages.items():
            match = re.search(r'date_updated:\s*(\d{4}-\d{2}-\d{2})', info['content'])
            if match and match.group(1) < latest_source_date:
                stale_pages.append(name)

    # Contradiction Scan - pages with contrastive keywords + multiple wikilinks
    contradiction_keywords = ['tuttavia', 'al contrario', 'invece', 'ma']
    pages_with_contrasts = []
    for name, info in all_pages.items():
        content_lower = info['content'].lower()
        for kw in contradiction_keywords:
            if (kw in content_lower and
                    len(re.findall(r'\[\[[^\]]+\]\]', content_lower)) > 3):
                pages_with_contrasts.append(name)
                break

    # Statistics - count by directory category (normalize to forward slashes)
    source_count = 0
    entity_count = 0
    concept_count = 0
    for n, v in all_pages.items():
        norm_path = v['path'].replace(os.sep, '/')
        if '/Wiki/sources' in norm_path or 'sources/' in norm_path:
            source_count += 1
        elif '/Wiki/entities' in norm_path or '/entities/' in norm_path:
            entity_count += 1
        elif '/Wiki/concepts' in norm_path or '/concepts/' in norm_path:
            concept_count += 1
    total_unique_links = len(set(link_sources.keys()))

    stats = {
        'total': len(all_pages),
        'sources': source_count,
        'entities': entity_count,
        'concepts': concept_count,
        'unique_links_used': total_unique_links,
        'broken_count': len(broken_links),
        'orphan_count': len(orphans),
        'stale_count': len(stale_pages),
        'contrast_pages': len(pages_with_contrasts),
    }

    return {
        'all_pages': all_pages,
        'broken_links': broken_links,
        'orphans': orphans,
        'stale_pages': stale_pages,
        'contradiction_candidates': pages_with_contrasts,
        'stats': stats,
    }


def suggest_fix(broken_name: str, existing_names: set) -> str:
    """Suggest the best-matching existing page for a broken wikilink."""
    lower_b = broken_name.lower().replace('-', ' ')
    for ex in existing_names:
        clean_ex = ex.lower().replace('-', ' ')
        if any(w in clean_ex for w in lower_b.split() if len(w) > 3):
            return f' -> [[{ex}]]'
    return ''


def print_report(results: dict) -> None:
    """Print human-readable lint report to stdout (ASCII-safe)."""
    stats = results['stats']

    print("=" * 70)
    print("WIKI LINT SCAN - Integrity & Health Check")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 70)

    # Broken Wikilinks
    broken = results['broken_links']
    existing_names = set(results['all_pages'].keys())
    print("\n--- 1. BROKEN WIKILINK CHECK ---")
    if broken:
        print(f"   [WARN] FOUND {len(broken)} BROKEN LINKS:")
        for bl, srcs in sorted(broken.items()):
            suggestion = suggest_fix(bl, existing_names)
            print(f"      - [[{bl}]] (from {', '.join(srcs[:2])}){suggestion}")
    else:
        print("   [OK] ALL WIKILINKS RESOLVE - 0 broken")

    # Orphan Pages
    orphans = results['orphans']
    print("\n--- 2. ORPHAN PAGE CHECK ---")
    if orphans:
        print(f"   [WARN] FOUND {len(orphans)} POTENTIAL ORPHANS:")
        for op in sorted(orphans):
            suggestion = suggest_fix(op, existing_names)
            print(f"      - [[{op}]] - NO INCOMING LINKS{suggestion}")
    else:
        print("   [OK] ALL PAGES HAVE AT LEAST ONE INCOMING LINK")

    # Stale Pages
    stale = results['stale_pages']
    print("\n--- 3. STALE PAGE CHECK ---")
    if stale:
        print(f"   [WARN] {len(stale)} pages have outdated date_updated:")
        for sp in sorted(stale)[:10]:
            print(f"      - [[{sp}]]")
        if len(stale) > 10:
            print(f"      ... and {len(stale) - 10} more (see JSON output)")
    else:
        print("   [OK] All entity/concept dates are current")

    # Contradictions
    contrasts = results['contradiction_candidates']
    print("\n--- 4. CONTRADICTION SCAN ---")
    if contrasts:
        print(f"   [INFO] {len(contrasts)} pages contain contrastive language - review manually:")
        for cp in sorted(contrasts)[:10]:
            print(f"      - [[{cp}]]")
        if len(contrasts) > 10:
            print(f"      ... and {len(contrasts) - 10} more (see JSON output)")
    else:
        print("   [OK] No obvious contradictions detected")

    # Summary Stats
    print("\n--- WIKI STATISTICS ---")
    print(f"   Total Pages: {stats['total']}")
    print(f"   Sources: {stats['sources']} | Entities: {stats['entities']} | Concepts: {stats['concepts']}")
    print(f"   Unique Wikilinks Used: {stats['unique_links_used']}")
    print(f"   Broken Links: {stats['broken_count']} | Orphans: {stats['orphan_count']}")


def export_json(results: dict, output_path: str) -> None:
    """Export lint results as JSON for programmatic consumption."""
    import json

    def make_serializable(obj):
        if isinstance(obj, set):
            return [str(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(k): make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(i) for i in obj]
        else:
            return obj

    serializable = {}
    for key, value in results.items():
        if key == 'all_pages':
            serializable[key] = {k: {'path': v['path']} for k, v in value.items()}
        else:
            serializable[key] = make_serializable(value)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved to: {output_path}")


def main():
    """CLI entry point - accepts wiki root path and optional output format."""
    import argparse

    parser = argparse.ArgumentParser(description="Wiki Lint Tool")
    parser.add_argument('--wiki-root', default=None, help='Path to Wiki/ directory (auto-detected if omitted)')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--output-json', default=None, help='Save JSON report to this path')

    args = parser.parse_args()

    # Determine wiki root
    wiki_root = args.wiki_root or find_wiki_root()
    if not wiki_root:
        print("ERROR: Cannot determine wiki root. Use --wiki-root <path>")
        sys.exit(1)

    print(f"Scanning wiki at: {wiki_root}\n")
    results = scan_wiki(wiki_root)

    if args.format == 'json':
        output_path = args.output_json or f'lint_report_{date.today().isoformat()}.json'
        export_json(results, output_path)
    else:
        print_report(results)
        if args.output_json and os.path.isdir(os.path.dirname(args.output_json)):
            export_json(results, args.output_json)


if __name__ == '__main__':
    main()
