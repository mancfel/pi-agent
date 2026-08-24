---
name: wiki-ingest
description: Standardized and detailed protocol for ingesting a raw source into Wiki/sources/, extracting entities into Wiki/entities/, and concepts into Wiki/concepts/.
---

# Wiki Ingest Skill

Use this skill when you need to process and convert a raw source file from `raw/` into the interconnected wiki knowledge base (Layer 2).

## Date Convention — Use System Date via Helper Script

**ALL dates in this skill must come from the system date at time of execution, never hardcoded or template values.**

```bash
# Get today's date (YYYY-MM-DD format):
python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py
# Output: 2026-08-24 (or whatever today actually is)
```

Use this value for:
- `date_updated:` frontmatter fields on all new/updated pages
- `Processed — YYYY-MM-DD` status lines in index.md
- `[YYYY-MM-DD]` log entry headings in log.md
- Any other timestamped field anywhere in the wiki

**Never use placeholder dates like `2025-10-19`, `2024-01-01`, or any static date.** If you are unsure what today's date is, run `wiki_date.py` before starting any write operation.

---

## Ingestion Workflow (Step by Step)

1. **Read `Wiki/index.md` First**:
   - Identify the source to ingest and verify it is marked as `Unprocessed`.
2. **Read the Source File Completely**:
   - Analyze the entire content of the raw file in `raw/` to thoroughly understand its contents and arguments (remember: **never modify the raw file**).
3. **Create the Source Summary (`Wiki/sources/`)**:
   - Create a file in `Wiki/sources/<CleanedSourceTitle>.md`.
   - Insert mandatory YAML frontmatter (`type: source-summary`).
   - Write a **strictly factual** summary (in Italian as per raw source context or English), without personal interpretations or external contamination.
   - Include key points, numerical data, and relevant quotes.
   - Use **Obsidian-style wikilinks** (`[[Entity Name]]`, `[[PascalCaseConceptName]]`, or aliased links `[[Target|Display Name]]`) extensively to connect mentions to their respective pages.
   - Create all the new files with extension `.md`
4. **Extract and Update Entities (`Wiki/entities/`)**:
   - Identify mentioned people, organizations, and tools.
   - Create or update files in `Wiki/entities/` specifying `entity_type: person | organization | tool` in the frontmatter.
   - Add a link to the new source in the related sources list.
   - **Avoid Orphan Pages**: Ensure every new or updated entity page has bidirectional links (incoming links from source summaries/concepts and outgoing links to related concepts/sources) so no entity remains unlinked.
   - Create all the new files with extension `.md`
5. **Extract and Update Concepts (`Wiki/concepts/`)**:
   - Identify discussed financial ideas, patterns, and techniques.
   - Create or update files in `Wiki/concepts/` (PascalCase.md) with frontmatter `type: concept`, `confidence: high|medium|low`.
   - Include nuance or contradiction blocks if the source diverges from existing concepts.
   - **Avoid Orphan Pages**: Ensure every concept page is densely connected via Obsidian wikilinks to relevant source summaries and related entities, preventing orphan or isolated pages.
   - Create all the new files with extension `.md`
6. **Update Operational Dashboards**:
   - **`Wiki/index.md`**: Change source status to `Processed — $(python wiki_date.py)` and update entity and concept tables.
   - **`Wiki/overview.md`**: Update statistics and emerging clusters if the big picture has changed significantly.
7. **Update `Wiki/log.md` (Append-Only)**:
   - Append a formal record at the bottom of the log with date, source path, created entities/concepts, and key themes.
8. **Report to the user**:
	- At the end of the task reply to the user with a brief report of what done but without describing the concepts ingested
		- Pages Created/Updated
		- Validation Results
		- Statistics on how many sources need to be still ingested (ingested files / total to ingest, in current folder and in general)
		- **Not Needed**: Key Content Highlights

---

## Pre-Ingest Checklist: Broken Link Prevention

Before creating any new files, scan existing wiki content to avoid orphan pages and broken wikilinks.

### Scan Existing Entity/Concept Pages
1. **Check for existing entity/concept pages** before creating new ones — if a person or concept already has a page (e.g., `[[John Bogle]]` exists), link to it instead of creating a duplicate.
2. **Identify Italian-language aliases** used in sources that should point to English-named pages:
   - `[[Behavioral Finance]]` → `[[Finanza Comportamentale|Behavioral Finance]]`
   - `[[Legge di Pareto]]` → `[[Pareto Principle|Legge di Pareto]]`
   - `[[Premio Nobel]]` → `[[4 Lezioni sulla Finanza da Premio Nobel|Premio Nobel]]`
   - `[[DCA]]` → `[[Dollar Cost Averaging|DCA]]`
   - `[[Investitori Attivi]]` → `[[Efficient Market Hypothesis|Investitori Attivi]]`
   - `[[Rischio Idiosincratico]]` → `[[Idiosyncratic Risk|Rischio Idiosincratico]]`
3. **Create missing entity/concept pages** for frequently mentioned people (e.g., [[Ben Carlson]], [[Meb Faber]], [[Nassim Taleb]]) and concepts (ETF, Drawdown, Beta, Momentum) that appear across multiple sources.
4. **Link new pages bidirectionally**: When creating a new entity page, add outgoing wikilinks to related concepts/sources from the same episode so it has immediate incoming links and doesn't become orphaned.

### Filename Sanitization Rules (CRITICAL)

Before creating any `.md` file, sanitize the intended filename by applying these rules **in order**:

1. **REPLACE `/` with `-`** — forward slash is a directory separator on ALL platforms; using it creates unintended subdirectories and breaks wikilinks. This is the #1 cause of broken wiki structure.
2. **REPLACE all other forbidden characters** with hyphens: `*`, `?`, `"`, `<`, `>`, `|`, `\`
3. **REPLACE colons `:`** with hyphens (problematic on Windows/macOS):
4. **REMOVE leading/trailing spaces**, then collapse multiple internal spaces to single hyphens
5. **NORMALIZE**: Use PascalCase or hyphenated format only — no underscores in final filenames, no mixed conventions
6. **VALIDATE**: The resulting filename must contain ONLY `[A-Za-z0-9_-]` plus `.md` extension

**Sanitization examples:**
```
P/E Ratio                        → PE-Ratio.md
Passion Asset / Passion Investment → Passion-Asset-Passion-Investment.md
Stock Rotation (Value/Growth)    → Stock-Rotation-Value-Growth.md
R > G - Piketty                  → R-G-Piketty.md
10_000 Lezioni                   → 10000-Lezioni.md
```

**Post-creation verification:** After writing any file, confirm it landed in the correct flat directory:
```bash
find Wiki/concepts/ -mindepth 2 -type f   # should return NOTHING
find Wiki/entities/ -mindepth 2 -type f   # should return NOTHING
find Wiki/sources/ -mindepth 2 -type f    # should return NOTHING
```
If this command returns files, they were placed in subdirectories — move them immediately and fix wikilinks.

For Italian-language references that should link to English pages, always use aliased syntax: `[[EnglishPageName|ItalianDisplay]]`

## Post-Ingest Validation: Fix Broken Links Immediately

After creating new files but before updating dashboards, run a quick validation:
1. **Verify all wikilinks resolve**: Check that every `[[...]]` reference points to an existing file on disk.
2. **Fix aliases in-place**: If a source uses an Italian alias like `[[Broker]]`, replace it with the correct target: `[[Broker, Asset Allocation e USA con Alessandro Saldutti|Broker]]` or create a dedicated concept page for common terms (ETF, DCA, Drawdown).
3. **Link orphan pages**: Ensure newly created entity/concept pages are linked from at least one other page (source summary or related concept) so they receive incoming links immediately.
4. **Ensure Relative Paths**: Ensure that all paths are relative to the wiki root folder and not absolute

## Reference Frontmatter Template
```yaml
---
type: source-summary
tags:
  - wiki/source-summary
date_updated: $(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)
tags: [wiki/source]
source_file: Clippings/Source-Name.md
authors: ["[[Author]]"]	      
---
```

## Automation Scripts (Reusable)

Python scripts for dashboard updates and wikilink validation live in the skill directory.

**Skill location:** `.pi/agent/skills/wiki-ingest/scripts/`
```bash
# Windows:
C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/

# macOS/Linux:
~/.pi/agent/skills/wiki-ingest/scripts/
```

### Setup: Make Scripts Available from Any Project

Choose ONE of these approaches to run scripts without typing full paths:

| Approach | Command | Best For |
|----------|---------|----------|
| **Symlink (recommended)** | `ln -s <SKILL_DIR>/scripts wiki-scripts` | Git-tracked projects, Linux/macOS |
| **Copy into project** | Copy both `.py` files → `<project>/wiki-scripts/` | Projects that must be self-contained |
| **Shell alias** | Add aliases to `.bashrc` / `.zshrc` | Quick access across all projects |

#### Setup Examples

```bash
# --- Option 1: Symlink (Linux/macOS, one-time per project) ---
cd <PROJECT_ROOT>
ln -s ~/.pi/agent/skills/wiki-ingest/scripts wiki-scripts
ls wiki-scripts/

# --- Option 1b: Junction (Windows, one-time per project) ---
cd projectRoot
mklink /J wiki-scripts C:\Users\<USER>\.pi\agent\skills\wiki-ingest\scripts
dir wiki-scripts

# --- Option 2: Copy into project ---
mkdir -p my-project/wiki-scripts
cp ~/.pi/agent/skills/wiki-ingest/scripts/*.py my-project/wiki-scripts/

# --- Option 3: Shell alias (one-time, global) ---
echo '# Wiki ingest scripts' >> ~/.bashrc
echo 'WIKI_SCRIPTS="$HOME/.pi/agent/skills/wiki-ingest/scripts"' >> ~/.bashrc
echo 'wiki-update-status() { python "$WIKI_SCRIPTS/wiki_update_status.py" "$@"; }' >> ~/.bashrc
echo 'wiki-validate-links() { python "$WIKI_SCRIPTS/wiki_validate_links.py" "$@"; }' >> ~/.bashrc
source ~/.bashrc
```

### Script A: `wiki_update_status.py` — Dashboard Update

**Purpose:** Batch update source statuses from `Unprocessed` → `Processed - <today's date>` by matching exact line strings in `index.md`. Always use `wiki_date.py` to get the current system date instead of hardcoding.

**Location:** `<project>/wiki-scripts/wiki_update_status.py` (after setup, see above)

```bash
# Using symlink approach:
cd <PROJECT_ROOT>
python wiki-scripts/wiki_update_status.py \
    --old '| 35 | [Old Title](path/file.txt) | FOLDER | Unprocessed |' \
    --new '| 35 | [New Cleaned Title](path/file.txt) | FOLDER | Processed - $TODAY |'

# Multiple sources (repeat --old/--new pairs):
python wiki-scripts/wiki_update_status.py \
    --old '| 35 | ... | Unprocessed |' --new '| 35 | ... | Processed - $TODAY |' \
    --old '| 36 | ... | Unprocessed |' --new '| 36 | ... | Processed - $TODAY |' \
    --old '| 37 | ... | Unprocessed |' --new '| 37 | ... | Processed - $TODAY |'

# Dry run (preview without writing):
python wiki-scripts/wiki_update_status.py \
    --old '| 35 | ... | Unprocessed |' --new '| 35 | ... | Processed - $TODAY |' \
    --dry-run
```

**Tips:**
- Always verify the exact line format in `index.md` first: `grep "Unprocessed" Wiki/index.md`
- The script prints `✗ NOT FOUND (skipped)` for lines that don't match exactly — no crash.
- You can batch-update dozens of entries at once. Max recommended: ~50 per run.

---

### Script B: `wiki_validate_links.py` — Wikilink Validation

**Purpose:** Scan markdown files for broken `[[wikilink]]` references that don't resolve to existing pages on disk.

**Location:** `<project>/wiki-scripts/wiki_validate_links.py` (after setup, see above)

```bash
# Using symlink approach:
cd <PROJECT_ROOT> && python wiki-scripts/wiki_validate_links.py Wiki/sources/New Episode.md

# Multiple files (mixed types):
python wiki-scripts/wiki_validate_links.py \
    sources/E1.md entities/New Person.md concepts/New Concept.md

# List-only mode (show all links without validation):
python wiki-scripts/wiki_validate_links.py Wiki/sources/E1.md --list-only
```

**Tips:**
- If "BROKEN" is reported, fix by creating the missing page or updating the wikilink to an existing target.
- The script builds `existing_pages` dynamically from disk — catches typos and naming mismatches automatically.
- For aliased links like `[[Target Page|Display Name]]`, only the part before `|` is validated.

---

### Combined Workflow: Scripts A + B Sequentially

For batch processing multiple sources, run Script A first (dashboard update), then Script B (link validation):

```bash
# Step 1: Get today's date first, then use it in status updates
TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)
python wiki-scripts/wiki_update_status.py \
    --old '| 35 | ... | Unprocessed |' --new "| 35 | ... | Processed - $TODAY |" \
    --old '| 36 | ... | Unprocessed |' --new "| 36 | ... | Processed - $TODAY |"

# Step 2: Validate any new entity/concept pages created during the batch
python wiki-scripts/wiki_validate_links.py \
    entities/New Person.md concepts/New Concept.md sources/E1.md sources/E2.md
```

---

### Log Entry (Append-Only Pattern)

Use this bash pattern to append a structured log entry after each ingest:

```bash
cat >> Wiki/log.md << 'LOGEOF'

## [$($ python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)] ingest | Cleaned Source Title (#NN)
- Source path: `raw/0X_Folder_Name/Filename.txt`
- Entity pages created/updated: [[Entity1]], [[Entity2]]
- Concept pages created/updated: [[Concept1]], [[Concept2]]
- Key themes: theme A, theme B, theme C (bullet-point style, max 3–5 lines)
LOGEOF
echo "Log entry appended"
```

**Tips:**
- **IMPORTANT**: For the log entry date, use unquoted heredoc (`<< LOGEOF`) so the `$(python wiki_date.py)` command expands to today's actual date:
```bash
TODAY=$(python C:/Users/<USER>/.pi/agent/skills/wiki-ingest/scripts/wiki_date.py)
cat >> Wiki/log.md << LOGEOF

## [$TODAY] ingest | Cleaned Source Title (#NN)
...
LOGEOF
```
- The quoted form (`<< 'LOGEOF'`) prevents ALL variable/command expansion — do NOT use it when you need dynamic dates.
- Always include a blank line before the `## [date]` heading to separate from previous entries.

---

### Quick Reference: Typical Ingest Sequence

For each new source:

| Step | Action | Tool / Script |
|------|--------|---------------|
| 1 | Create source summary file | `write` tool → `Wiki/sources/<Title>.md` |
| 2 | Create/update entity pages | `write` tool → `Wiki/entities/Name.md` |
| 3 | Create/update concept pages | `write` tool → `Wiki/concepts/Concept.md` |
| 4 | Validate wikilinks | **Script B**: `wiki_validate_links.py` |
| 5 | Fix any broken links found | Manual edit or re-create affected pages |
| 6 | Update dashboard (index.md) | **Script A**: `wiki_update_status.py` |
| 7 | Append to log | Bash pattern: `cat >> Wiki/log.md << 'LOGEOF' ... LOGEOF` |

**Batch processing:** When ingesting multiple sources at once, run Script A once for all status updates and Script B once for all new files. The bash log pattern can be combined into a single append.

```bash
# Example batch: update statuses + validate + log in sequence
python wiki-scripts/wiki_update_status.py --old '| 35 |...| Unprocessed|' --new '| 35 |...| Processed - $TODAY|'
python wiki-scripts/wiki_validate_links.py Wiki/entities/New Person.md Wiki/concepts/New Concept.md
```

### Running Scripts from Any Directory

After setting up a symlink (`wiki-scripts/`), run scripts from any subdirectory of your project:

```bash
# From anywhere inside the project:
cd <PROJECT_ROOT>/Wiki && python ../wiki-scripts/wiki_update_status.py --help
cd <PROJECT_ROOT>/raw && python ../../wiki-scripts/wiki_validate_links.py ../Wiki/sources/File.md
```

The `--wiki-dir` flag lets you point to any Wiki directory regardless of CWD:

```bash
python wiki-scripts/wiki_update_status.py \
    --old '|' 35 |...|' --new '| 35 |...|' \
    --wiki-dir D:/other-project/Wiki
```
