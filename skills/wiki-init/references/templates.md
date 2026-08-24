# Template di Riferimento per la LLM Wiki

Questo documento contiene i template standard per i file strutturali della wiki e per la sezione di schema in `AGENTS.md`.

## 1. `Wiki/index.md`

```markdown
---
type: index
date_updated: 2026-08-24
tags: [wiki/index, wiki/meta]
---

# Wiki Index

## Unprocessed Sources
- [ ] Clippings/Example-Source.md

## Sources Summary
| Source | Date Ingested | Key Entities |
| ------ | ------------- | ------------ |
| [[Source Summary Name]] | YYYY-MM-DD | [[Entity 1]], [[Entity 2]] |

## Entities
| Entity | Type | Sources |
| ------ | ---- | ------- |
| [[Entity Name]] | Person / Tool / Org | 2 |

## Concepts
| Concept | Confidence | Sources |
| ------- | ---------- | ------- |
| [[Concept Name]] | High | 3 |

## Synthesis
| Query / Synthesis | Date |
| ----------------- | ---- |
| [[Synthesis Title]] | YYYY-MM-DD |
```

## 2. `Wiki/log.md`

```markdown
---
type: log
date_updated: 2026-08-24
tags: [wiki/log, wiki/meta]
---

# Wiki Operation Log

## [2026-08-24] init | Initialized LLM Wiki structure
- Created directory structure (`sources/`, `entities/`, `concepts/`, `synthesis/`)
- Initialized `index.md`, `log.md`, and `overview.md`
- Configured `AGENTS.md` schema
```

## 3. `Wiki/overview.md`

```markdown
---
type: overview
date_updated: 2026-08-24
tags: [wiki/overview, wiki/meta]
---

# Domain Overview

> High-level synthesis and mental model of the knowledge base domain.

## Core Themes
- Theme 1 ([[[Concept 1]]])
- Theme 2 ([[[Concept 2]]])

## Key Findings & Architecture
- Summary of current understanding across all ingested sources.
```

## 4. Sezione Schema per `AGENTS.md`

Aggiungi questo blocco al file `AGENTS.md` del progetto:

```markdown
## LLM Wiki Maintenance Schema

You are the designated maintainer of the persistent interlinked wiki located in `Wiki/`. Follow these architectural rules and operational procedures:

### Core Rules
1. **Raw Sources Are Immutable**: Never modify files in raw source folders (e.g. `Clippings/`). Read them fully, but leave them untouched.
2. **You Own `Wiki/` Entirely**: Generate and maintain all markdown files within `Wiki/`. Never hand-edit wiki pages unless requested, but you have full autonomy to update them.
3. **Always Update `index.md` and `log.md`**: On every single ingest, query synthesis, or structural change, update `Wiki/index.md` and append an entry to `Wiki/log.md` using the format `## [YYYY-MM-DD] operation | Title`.
4. **Factual vs. Interpretive**: Keep source summaries in `Wiki/sources/` strictly factual. Put interpretations, mental models, and synthesis in `Wiki/concepts/` and `Wiki/synthesis/`.
5. **Handle Contradictions**: When new sources contradict existing wiki content, note the contradiction explicitly in concept pages rather than silently overwriting.

### Page Conventions
- **Frontmatter**: Every wiki page must have YAML frontmatter with `type:` (`source-summary`, `entity`, `concept`, `synthesis`) and `date_updated:`.
- **Tags**: Use namespaced tags (`wiki/source`, `wiki/entity`, `wiki/concept`, `wiki/synthesis`).
- **Wikilinks**: Use heavy `[[wikilinks]]` for all entity, concept, and source references to empower Obsidian graph view.
- **Dataview**: Use inline metadata `[key::value]` where appropriate.
- **Confidence**: Concept pages should include `confidence: high | medium | low`.

### Operations
- **Ingest**: Read raw source -> create source summary in `Wiki/sources/` -> create/update entities and concepts -> update `Wiki/index.md` and `Wiki/overview.md` -> append to `Wiki/log.md`.
- **Query**: Read `Wiki/index.md` -> read relevant wiki pages -> synthesize answer with wikilinks -> file as new page in `Wiki/synthesis/` if substantial -> update index and log.
- **Lint**: Periodically check for orphan pages, broken wikilinks, stale pages (`date_updated` older than newest relevant source), and unlinked concepts.
```
