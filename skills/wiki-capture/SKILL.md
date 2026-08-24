---
name: wiki-capture
description: Standardized guide and protocol for identifying, cataloging, and registering new raw source files in the raw/ source folder before wiki ingestion.
---

# Wiki Capture Skill

Use this skill when you need to identify, catalog, and register new raw transcript or article files within the `raw/` folder before they are processed into the wiki (Layer 2).

## Core Principles
- **Absolute Immutability (Layer 1)**: Raw files in `raw/` must NEVER be modified, renamed, or deleted. They represent the immutable ground truth.
- **Source Traceability**: Every new file must be mapped in the central catalog (`Wiki/index.md`) with its exact relative path.

## Operational Workflow

1. **Scan the `raw/` Folder**:
   - Explore the root or subfolders of the `raw/` directory to locate unprocessed or newly added transcription files.
2. **Check Presence in `Wiki/index.md`**:
   - Open `Wiki/index.md` (following the Read First protocol) and check if the file is already listed in the unprocessed sources table.
   - If not present, add it to the respective topic folder table with `Unprocessed` status.
3. **Log Acquisition**:
   - If new source files are added, record the event in the append-only log `Wiki/log.md` (if applicable) or prepare references for the subsequent ingestion phase.

## Cataloging Example in `Wiki/index.md`
```markdown
| # | Source File | Topic Folder | Status |
|---|-------------|-------------|--------|
| n | [File Title](raw/folder/filename.txt) | folder_name | Unprocessed |
```
