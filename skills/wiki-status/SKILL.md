---
name: wiki-status
description: Standardized protocol and guide for inspecting, reporting, and summarizing the operational status, metrics, and dashboard of the Bull Investment Wiki.
---

# Wiki Status Skill

Use this skill when you need to inspect, evaluate, or report the current operational status, quantitative metrics, processing progress, and recent activity of the Bull Investment Wiki.

## Core Principles
- **Index-First Dashboard**: `Wiki/index.md` and `Wiki/overview.md` serve as the central control panel and table of contents. Always inspect them first to assess the state of the knowledge base.
- **Quantitative Transparency**: A clear status report tracks source ingestion progress, entity/concept growth, synthesis coverage, and recent log activity.

---

## Operational Workflow

### 1. Review Central Dashboards
- Open `Wiki/index.md` to check the catalog of sources (processed vs. unprocessed) and registered synthesis pages.
- Read `Wiki/overview.md` to check high-level macro-syntheses and structural developments.

### 2. Compute Knowledge Base Metrics
Gather and report counts across the wiki directories:
- **Raw Sources (`raw/`) vs. Source Summaries (`Wiki/sources/`)**: Total available sources vs. ingested and summarized sources.
- **Processing Progress**: Number of processed sources vs. unprocessed sources remaining.
- **Entities (`Wiki/entities/`)**: Total people, organizations, and concepts cataloged as entities.
- **Concepts (`Wiki/concepts/`)**: Total ideas, patterns, and techniques cataloged, including confidence distribution.
- **Synthesis Pages (`Wiki/synthesis/`)**: Total thematic query answers filed back into the wiki.

### 3. Review Recent Activity (`Wiki/log.md`)
- Inspect the last 5-10 entries in `Wiki/log.md` to understand recent ingestions, queries, lints, or remediation operations.

### 4. Generate Status Report
Compile findings into a structured summary report following the template below.

---

## Status Report Template

```markdown
## 📊 Wiki Status Report — $TODAY
(where `$TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)`)

### 1. Source Processing Metrics
- **Total Raw Sources**: N
- **Processed Sources**: M (Registered in `Wiki/sources/`)
- **Unprocessed Sources**: K
- **Completion Rate**: X%

### 2. Knowledge Base Assets
- **Entities (`Wiki/entities/`)**: A pages
- **Concepts (`Wiki/concepts/`)**: B pages
- **Synthesis Pages (`Wiki/synthesis/`)**: C pages

### 3. Recent Activity (Last Operations)
- Last Ingestion: `<Source Title>` on $TODAY
- Last Lint / Health Check: $TODAY (0 broken links)
- Last Operations Logged:
  - `[YYYY-MM-DD] <action> | <details>`

### 4. Health & Recommendations
- Pending unprocessed sources or integration gaps.
- Recommended next actions (e.g., ingest next source batch, run lint, update stale pages).
```

---

## Best Practices
- **Non-Destructive**: Inspecting wiki status is entirely read-only; do not modify wiki files unless an explicit ingestion, query, or maintenance operation is requested.
- **Traceability**: Always cross-check counts against `Wiki/index.md` and `Wiki/log.md` to ensure absolute consistency.
