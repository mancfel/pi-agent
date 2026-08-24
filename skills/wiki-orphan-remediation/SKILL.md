---
name: wiki-orphan-remediation
description: Standardized protocol and guide for identifying and linking orphan pages (entity, concept, or source summary nodes with zero incoming wikilinks) to maximize Obsidian graph connectivity and knowledge network density.
---

# Wiki Orphan Page Remediation Skill

Use this skill when you need to identify, analyze, and resolve orphan pages (pages that have zero incoming wikilinks from any other page in the wiki) to improve the density and navigability of the Obsidian knowledge graph.

## Core Principles
- **Graph Density**: A healthy knowledge base has high connectivity. Orphan pages represent isolated islands of information that should be integrated into the conceptual network.
- **Leaf vs. Core Nodes**: Source summaries (`Wiki/sources/`) naturally act as leaf nodes (they summarize raw sources and point outwards to entities/concepts, but rarely receive incoming links). Entity and concept pages (`Wiki/entities/`, `Wiki/concepts/`), however, MUST receive at least one incoming wikilink.

---

## Operational Workflow

### 1. Identify Orphan Pages
- Run `wiki_lint.py` (from the `wiki-lint` skill) or inspect the JSON report (`wiki_lint_report.json`) to get the exact list of orphan pages.
- Categorize orphans into:
  - **Source summaries (`Wiki/sources/`)**: Generally expected leaf nodes. Check if they are referenced by any index or synthesis; otherwise, they can be noted as leaf nodes.
  - **Entity/Concept pages (`Wiki/entities/`, `Wiki/concepts/`)**: Action required — these must be linked.

### 2. Establish Inbound Links for Entities & Concepts
For each orphan entity or concept page:
1. **Locate supporting sources or related concepts**: Check which raw sources mention this entity/concept (consult `Wiki/sources/` or `Wiki/index.md`).
2. **Add incoming wikilinks**:
   - Add a wikilink to the orphan page inside the relevant source summary (e.g., in a "Menzioni ed Entità" or "Concetti Correlati" section).
   - Alternatively, link it from a broader parent concept page (e.g., linking a specific factor model concept from `[[Factor Investing]]`).
3. **Ensure Bidirectional Linking**:
   - Ensure the orphan page also links OUT to its sources and related concepts, maintaining robust two-way connectivity.
4. **Ensure Relative Paths**: Ensure that all paths are relative to the wiki root folder and not absolute

### 3. Log Remediation in `Wiki/log.md`
Append an entry to `Wiki/log.md` detailing the remediation action:

```markdown
## [$TODAY] orphan-remediation |
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`)
 Linked orphan entity/concept pages
- Orphan pages linked: [[Page1]], [[Page2]] (linked from [[SourceSummaryX]] and [[ConceptY]])
- Graph connectivity status: All active entities/concepts integrated into the wikilink network.
```

---

## Best Practices
- **Never delete valid entity/concept pages** just because they are orphans; always link them instead.
- **Use descriptive context** when adding links so the connection between the linking page and the orphan page is semantically meaningful.
