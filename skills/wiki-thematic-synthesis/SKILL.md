---
name: wiki-thematic-synthesis
description: Standardized protocol and guide for creating cross-cutting thematic synthesis pages in Wiki/synthesis/ to answer complex investment queries, connect disparate concepts, and synthesize macro-trends.
---

# Wiki Thematic Synthesis Skill

Use this skill when you need to answer complex investment queries, analyze overarching macro-trends, or synthesize insights across multiple source summaries, entities, and concepts by filing a structured synthesis page in `Wiki/synthesis/`.

## Date Convention — Use System Date via Helper Script

**ALL dates must come from the system date at time of execution.**

```bash
python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py
# Output: 2026-08-24 (today's actual system date)
```

Apply this value for:
- `date_updated:` frontmatter on new synthesis pages
- `[YYYY-MM-DD]` log entry headings in log.md
- Never use placeholder or hardcoded dates.

## Core Principles
- **Cross-Source Synthesis**: Synthesis pages go beyond single-source summaries or individual concept definitions. They integrate multiple perspectives, compare methodologies, and structure comprehensive answers to complex investment questions.
- **Permanent Knowledge Artifact**: Substantial answers (>200 words of original synthesis) are filed back into the wiki so future queries can build directly upon them without re-deriving answers from scratch.

---

## Operational Workflow

### 1. Review Existing Wiki Assets
- **Read `Wiki/index.md` first**: Identify relevant source summaries, entity pages, and concept pages related to the thematic query.
- **Read Wiki pages only**: Rely on the wiki layer (not raw sources) as the primary knowledge base. If critical gaps exist, note them.

### 2. Synthesize Answer & Structure Page
Create a new file in `Wiki/synthesis/<DescriptiveTopicName>.md` with the following structure. **Filename rules:** use hyphens only (no spaces, slashes, or special chars). Example: `Factor-Investing-Evidence-Implementation-Limits.md`. Never include `/`, `*`, `?`, `"`, `<`, `>`, `|`, or `:` — these create broken paths on disk.
- **YAML Frontmatter (REQUIRED)**:
  ```yaml
  ---
  type: synthesis
  tags:
    - wiki/synthesis
  date_updated: $(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)
  ---
  ```
- **Title & Overview**: Clear descriptive title and executive summary of the synthesis.
- **Core Arguments / Analysis**: Detailed breakdown synthesizing multiple sources and concepts, using heavy `[[wikilinks]]`.
- **Trade-offs and Contradictions**: Highlight differing views or mixed empirical evidence across sources.
- **Supporting Pages**: Bulleted list linking all supporting entity, concept, and source-summary pages used.
- **Ensure Relative Paths**: Ensure that all paths are relative to the wiki root folder and not absolute

### 3. Register in `Wiki/index.md`
- Add the new synthesis page to the **Synthesis Pages** table in `Wiki/index.md`.

### 4. Log Synthesis in `Wiki/log.md`
Append an entry to `Wiki/log.md`:

```markdown
## [$TODAY] synthesis | <Query Topic>
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`)

- Answer filed in: [[Wiki/synthesis/DescriptiveTopicName]]
- Supporting pages: [[Entity1]], [[Concept1]], [[Wiki/sources/SourceTitle]]
```

---

## Best Practices
- **Heavy Wikilinking**: Ensure every entity, concept, and source mentioned is wrapped in `[[wikilinks]]` to maintain graph cohesion.
- **Language**: Synthesis pages can be in Italian or English, favoring the language most practical for the query context while respecting local domain terminology.
- **Ask the user**: In case the topic to synthetize isn't specified by the user find some relevant topics not yet synthetized and use the `ask_user_question` tool and ask the user on what topic focus on.
