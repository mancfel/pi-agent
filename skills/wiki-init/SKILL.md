---
name: wiki-init
description: Initializes and structures a new LLM-managed wiki in an Obsidian vault or project folder from scratch, following Karpathy's llm-wiki pattern (immutable raw sources, LLM-managed wiki, schema in AGENTS.md, indexing with Ingest/Query/Lint operations).
---

# LLM Wiki Initialization (`wiki-init`)

This skill guides the agent and user through creating and configuring a persistent, interlinked, LLM-managed wiki (inspired by Karpathy's llm-wiki pattern) starting from an empty folder or existing Obsidian vault.

## Architecture Overview

The wiki is built on three layers:
1. **Raw Sources (`Clippings/` or similar)**: Original articles, notes, and documents. They are **immutable**: the LLM reads them but never modifies them.
2. **The Wiki (`Wiki/`)**: Interlinked markdown structure generated and maintained entirely by the LLM (source summaries, entity pages, concept pages, and synthesis pages).
3. **The Schema (`AGENTS.md`)**: Operational instructions and configuration that make the agent a disciplined wiki maintainer.

---

## Initialization Algorithm (Step by Step)

Follow these steps rigorously to initialize the wiki:

### 1. Tooling and Environment Setup
- **Local Attachments Folder**: Configure the attachments folder at `assets/` (e.g., in `.obsidian/app.json`: `{"attachmentFolderPath": "assets/"}`) and set the attachment download shortcut (e.g., `Ctrl+Shift+D` in `.obsidian/hotkeys.json`).
- **Obsidian CLI**: Check for and register the Obsidian CLI (if available) and add it to the `PATH` so the agent can read, create, search, and manage notes programmatically.
- **Advanced Search with `qmd`**: As the project grows, configure `qmd` for hybrid BM25/vector search and MCP server support.

### 2. Directory Structure Scaffolding (`Wiki/`)
Create the directory structure and starter files:
```bash
mkdir -p Wiki/{sources,entities,concepts,synthesis}
```

Create the essential files (see `references/templates.md` for complete templates):
- **`Wiki/index.md`**: Content catalog with tables for sources, entities, concepts, and synthesis pages, plus a list of unprocessed sources (*Unprocessed Sources*). The agent reads this file first.
- **`Wiki/log.md`**: Append-only operation log (entry format: `## [YYYY-MM-DD] operation | Title`).
- **`Wiki/overview.md`**: High-level synthesis of the entire wiki domain.

### 3. Schema in `AGENTS.md`
Add or update the **"LLM Wiki"** section in the project's `AGENTS.md` file (see `references/templates.md` for the default schema block). This section must document:
- Wiki architecture and structure.
- Page conventions:
  - Mandatory YAML frontmatter with `type:` (`source-summary`, `entity`, `concept`, `synthesis`).
  - Tag namespace with `wiki/` prefix (e.g., `wiki/source`, `wiki/entity`).
  - Heavy use of `[[wikilinks]]` for Obsidian Graph View visualization.
  - Frontmatter metadata `date_updated:`, `source_count:`, `confidence:` (high/medium/low) and inline Dataview `[key::value]` metadata.
- Operational procedures:
  - **Ingest**: Full raw source reading from `raw/` -> summary in `Wiki/sources/` -> entity creation/update in `Wiki/entities/` and concept creation/update in `Wiki/concepts/` -> update `Wiki/index.md` and `Wiki/overview.md` -> append to `Wiki/log.md`.
  - **Query**: Consult `index.md` -> read wiki pages -> synthesize answer with wikilinks -> file back into `Wiki/synthesis/` if substantial enough -> update index and log.
  - **Lint**: Periodic health check of the wiki (orphan pages, broken links, stale pages, contradictions, concepts mentioned without a page).
- Key rules:
  - Never modify raw sources.
  - Always update `index.md` and `log.md` on every modification.
  - Keep source summaries factual; interpretation belongs in concept/synthesis pages.
  - Explicitly document contradictions between sources.

### 4. Calibration and Test Ingest
Before proceeding to massive processing, have the agent ingest 2–3 rich sources interactively to calibrate templates and gather user feedback.

### 5. Recommended Plugins and Best Practices
- **Obsidian Plugins**: *Dataview* (dynamic queries on frontmatter), *Obsidian Web Clipper* (article-to-markdown conversion), *Graph View*, *Tasks*.
- **Best Practice**: Start small, let the LLM write everything inside `Wiki/`, file back query answers, and perform periodic lint checks.
