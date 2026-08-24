---
name: wiki-stale-update
description: Standardized protocol and guide for updating stale entity and concept pages whose update date predates recent source ingestion batches, ensuring the knowledge base reflects the latest evidence.
---

# Wiki Stale Page Update Skill

Use this skill when you need to identify and refresh stale entity and concept pages whose `date_updated` frontmatter field predates newer source ingestion dates, integrating new claims, data points, or perspective shifts.

## Core Principles
- **Cumulative Knowledge**: The wiki compounds over time. When new sources are ingested, existing concept and entity pages should be updated to incorporate new perspectives, empirical data, or contradictions.
- **Traceability**: Every update must preserve existing historical claims while explicitly noting new evidence from recent source summaries (`Wiki/sources/`).

---

## Operational Workflow

### 1. Identify Stale Pages
- Run `wiki_lint.py` (from the `wiki-lint` skill) or inspect the JSON report (`wiki_lint_report.json`) to find pages where `date_updated` is older than the newest source ingestion date.
- Prioritize core concept pages (`Wiki/concepts/`) and major entity pages (`Wiki/entities/`) that have been mentioned in recent source ingestions.

### 2. Review New Sources & Extract Insights
- Read the newly ingested source summaries that reference the target entity or concept.
- Identify new arguments, supportive data, or contrasting opinions introduced by the new sources.

### 3. Update Page Content and Frontmatter
- **Incorporate New Findings**: Add a dedicated subsection (e.g., `## Aggiornamenti Recenti ($TODAY)`
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`)) or integrate seamlessly into existing prose) detailing what new sources add.
- **Handle Contradictions**: If new sources contradict previous claims, follow the *Contradiction Protocol* (do not overwrite; present both viewpoints explicitly).
- **Update Frontmatter**: Advance `date_updated` using: `$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)` and increment `source_count` if applicable.

### 4. Log Update in `Wiki/log.md`
Append an entry to `Wiki/log.md`:

```markdown
## [$TODAY] stale-update |
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`)
 Refreshed stale pages with recent source data
- Stale pages updated: [[EntityOrConcept1]], [[EntityOrConcept2]]
- New sources integrated: [[Wiki/sources/SourceTitleA]], [[Wiki/sources/SourceTitleB]]
```

---

## Best Practices
- **Do not overwrite past consensus**: Always attribute new findings to their respective source summaries via wikilinks.
- **Check cross-references**: Ensure updated pages maintain bidirectional links with all newly referenced sources.
