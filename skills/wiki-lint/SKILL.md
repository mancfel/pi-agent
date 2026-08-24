---
name: wiki-lint
description: Health-check and periodic verification protocol for the wiki to detect orphan pages, broken wikilinks, conflicts, and structural coherence.
---

# Wiki Lint Skill

Use this skill when you need to perform an integrity and health check on the wiki knowledge base.

## Tool: `wiki_lint.py`

A Python script is provided at `wiki_lint.py` in this directory. Use it as your primary scanning engine — do **not** write ad-hoc scripts or grep commands for lint checks.

### Usage

```bash
# From anywhere (auto-detects Wiki/ relative to project root):
python3 C:/Users/super/.pi/agent/skills/wiki-lint/wiki_lint.py

# Or specify a custom wiki root:
python3 C:/Users/super/.pi/agent/skills/wiki-lint/wiki_lint.py --wiki-root "D:/projectRoot/Wiki"

# Export JSON report for programmatic use:
python3 C:/Users/super/.pi/agent/skills/wiki-lint/wiki_lint.py --format json --output-json lint_report.json
```

### Output Format

The tool prints a human-readable report with four sections:

1. **Broken Wikilinks** — lists every `[[Name]]` that doesn't resolve to an existing file, plus suggestions for the best matching target page.
2. **Orphan Pages** — pages receiving zero incoming wikilinks from any other wiki page.
3. **Stale Pages** — entity/concept pages whose `date_updated` predates the newest source ingestion date.
4. **Contradiction Candidates** — pages containing contrastive keywords (`tuttavia`, `al contrario`, etc.) alongside multiple wikilinks — flag these for manual review.

It also prints summary statistics (total pages by category, unique links used, counts of each issue type).

## Main Checks & Actions

### 1. Broken Wikilinks (Run tool first)
- Run `wiki_lint.py` to get a full list with suggestions.
- For each broken link:
  - If it's a missing entity/concept → create the page following naming conventions from `wiki-ingest`.
  - If it's an Italian alias mismatch → apply `[TargetPage|ItalianDisplay]` syntax instead of renaming files.
  - If it references a source file that exists but has a different name → fix the wikilink to match the actual filename on disk.
- *Action*: Fix or remove dangling references. Re-run tool after fixes to confirm zero remaining.

### 2. Orphan Pages (Run tool first)
- The tool lists all pages with no incoming links.
- For each orphan:
  - **Source summaries** are expected to be leaf nodes — they don't normally receive incoming links from concepts/entities, only outbound ones. These can typically be ignored unless truly isolated from any related concept page.
  - **Entity/Concept pages** MUST have at least one inbound link. Link them from relevant source summaries where they were mentioned during ingestion, and add a "Relazioni con Altri Concetti" section pointing back to those sources for bidirectional connectivity.
- *Action*: Add incoming wikilinks from the most relevant source summary or concept page.

### 3. Contradictions (Manual review)
- The tool flags pages containing contrastive keywords alongside multiple wikilinks as candidates.
- Read each flagged page carefully:
  - If it contains a genuine contradiction with another wiki page → document BOTH views explicitly using language like: *"Source X claims [A], while Source Y argues [not-A]. The evidence is mixed because..."*
  - **Never silently overwrite** existing claims — follow the Contradiction Protocol in `CLAUDE.md`.
- *Action*: Document contradictions in prose on both affected pages; do not auto-resolve them.

### 4. Stale Pages (Run tool first)
- The tool compares every entity/concept `date_updated` against the newest source ingestion date.
- For each stale page:
  - Read the latest sources that mention this entity or concept.
  - Update the page's content and `date_updated` with new information from those sources.
  - Add a "Nuove Informazioni" section if the update is significant.
- *Action*: Update affected pages and verify `date_updated` reflects today's date.

### 5. Absolute paths
- Ensure that all paths are relative to the wiki root folder and not absolute

### 6. Log Results in `Wiki/log.md` (Append-Only)
After completing all fixes, append an entry to `Wiki/log.md`:

```markdown
## [$TODAY] lint |
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`) <Brief description>
- Broken links fixed: N (list categories — e.g., missing entities, Italian aliases)
- Orphan pages linked: M (list which were linked and from where)
- Stale pages updated: K
- Contradictions noted: [[PageA]] vs [[PageB]] on topic X
- Tool output: wiki_lint.py scan completed, 0 issues remaining
```

## Linting Log Example
```markdown
## [2025-08-18] lint | Post-ingest integrity check + full remediation
- Broken links fixed: 52 total (39 missing entity/concept pages created; 13 Italian aliases corrected via `[Target|Display]` syntax)
- Orphan pages linked: 12 entity/concept pages now have inbound links from relevant source summaries
- Stale pages updated: 0
- Contradictions noted: [[Factor Premiums]] vs [[Index Investing Limits]] on factor sustainability debate
- Tool output: wiki_lint.py scan completed, 0 issues remaining
```

## Best Practices

### Before Running the Tool
- Ensure all recent ingestions are complete and `Wiki/index.md` is up to date.
- If you just finished an ingestion batch, run lint immediately after — it's easier to fix broken links when the source context is fresh in your mind.

### After Fixing Issues
1. **Re-run the tool** to verify zero remaining issues before logging results.
2. **Update `Wiki/log.md`** with a structured entry (append-only, never edit past entries).
3. **Check bidirectional linking**: every newly created entity/concept page should link TO related pages AND receive at least one incoming wikilink from another page.

### Common Fixes Quick Reference

| Issue | Fix Pattern | Example |
|-------|-------------|---------|
| Missing entity/concept | Create new `.md` page with proper frontmatter | `[[R-G-Piketty]]` → create `concepts/R-G-Piketty.md` |
| Italian alias mismatch | Use `[TargetPage\|ItalianDisplay]` syntax | `[[Behavioral Finance]]` → `[[Finanza Comportamentale\|Behavioral Finance]]` |
| Wrong filename in link | Match exact file stem on disk | `[[60/40 Portfolio]]` → `[[60-40 Portfolio]]` (file is named `60-40 Portfolio.md`) |
| Orphan entity/concept | Link from relevant source summary + add outgoing relations section | Add `* [[ConceptName]]` to source's "Relazioni" section |
