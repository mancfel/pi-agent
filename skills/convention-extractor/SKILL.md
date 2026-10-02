---
name: convention-extractor
description: Adapter for lisyoen/convention-extractor — invokes the external Python tool, validates its output ({lang}_convention.md, conventions.json, refactoring_needed_*.txt), and constructs CONVENTIONS.md while preserving curated notes via --merge flag.
---

# Convention Extractor Skill (`convention-extractor`)

Use this skill to generate or regenerate `CONVENTIONS.md` (alias compatible with `conventions.md` if required by the repository) from source code analysis using `lisyoen/convention-extractor`. This skill **isolates** the external dependency; it can be swapped without affecting core workflow skills.

> **AGENTS.md Rule**: Per AGENTS.md § Pre-Planning & Implementation Context Check, other skills MUST read `CONVENTIONS.md` before planning or implementing. This skill is responsible for creating/updating that file when conventions change.

## Execution Model — Single Agent, Foreground Only

> Run every command directly. Do NOT spawn a background process for extraction.
>
> - Execute `extract_conventions.py` inline and wait for completion before proceeding.
> - Validate outputs immediately after invocation.
> - If the tool fails, report the error and attempt manual fallback in the same session.

## Admitted Input States
- Any state — convention extraction is independent of feature lifecycle states.

## Prerequisites

The wrapper script validates these before invoking the extractor:

| Requirement | Command | Fallback |
| ----------- | ------- | -------- |
| Python 3.6+ | `python --version` | Document failure and skip extraction |
| `requests` package | `python -c "import requests"` | Install via pip or fail gracefully |
| `pyyaml` package | `python -c "import yaml"` | Install via pip or fail gracefully |

On Windows, use `install.bat` (provided by the extractor) for pinned dependency installation.

## Configuration Precedence

Configuration is resolved in this order (highest to lowest priority):

1. **CLI flags** — e.g., `--threshold`, `--lang`, `-o`, `--api-base`
2. **Environment variables**:
   - `CONVENTION_API_BASE` — OpenAI-compatible API base URL
   - `CONVENTION_API_KEY` — API key (never written to artifacts)
   - `CONVENTION_MODEL` — Model name to use
3. **`config.yaml`** — local configuration file
4. **Defaults** — `http://localhost:11434/v1` for API base, no model specified

> **IMPORTANT**: Never include `config.yaml`, `api_key`, or any credential in versioned artifacts. Add `config.yaml` and `.env` to the repository's ignore list if not already present.

## Invocation

### Via Wrapper Script

```bash
python C:/Users/super/.pi/agent/skills/convention-extractor/scripts/extract_conventions.py \
    --target-dir "D:/projectRoot" \
    --lang python \
    --threshold 90 \
    --merge D:/projectRoot/CONVENTIONS.md \
    --output D:/projectRoot/generated_convention.md
```

### Direct Tool (Advanced)

The underlying tool supports these options:
- `--lang <language>` — Target language (`python`, `typescript`, etc.)
- `-o <outdir>` — Output directory for generated files
- `--skip-compliance` — Skip compliance check, only extract conventions
- `--threshold <N>` — Adoption threshold percentage (default: 90%)
- `--api-base <URL>` — Override API base URL
- `--model <name>` — Override model name
- `--merge <existing_file>` — Merge with an existing convention file to preserve curated notes
- `--ignore-file <path>` — Path to `.convention-ignore` file

### `.convention-ignore` File

Uses gitignore-style syntax to exclude paths from analysis:
```
# Ignore test directories
tests/
__tests__/
*.test.*
*.spec.*

# Ignore generated files
dist/
build/
node_modules/
venv/
```

## Output Validation

After invocation, the wrapper script validates that these output files exist and are non-empty:

| Expected Output | Description | Validation Check |
| --------------- | ----------- | ---------------- |
| `{lang}_convention.md` | Convention document for the language | File exists, >10 lines |
| `conventions.json` | Adoption percentages per convention rule | Valid JSON, has adoption scores |
| `refactoring_needed_YYYYMMDD_hhmmss.txt` | Files not conforming to conventions | Exists (may be empty if all conform) |
| Log file(s) | Run log + debug logs on error | Existence check only |

If any required output is missing or empty, the script writes an error message and returns exit code 1.

## Merging with Curated Notes (`--merge`)

When regenerating conventions:
1. Pass `--merge <existing_convention.md>` to preserve manually curated notes.
2. The native merge flag replaces generated sections while keeping user-added content intact.
3. After merging, verify that the curated notes section still exists in the output.
4. If the merge fails, fall back to manual merge (see below).

### Manual Merge Fallback

If the native `--merge` fails:
1. Read both files fully.
2. Preserve any section after `---` or under a heading like "Curated Notes" or "Manual Additions".
3. Insert the new generated conventions before the preserved notes.
4. Update the header metadata (timestamp, tool version) but keep existing author fields.

## Output Artifacts Location

All outputs go to the repository root by default:
- `CONVENTIONS.md` — Final merged convention document
- `{lang}_convention.md` — Raw extracted convention for reference
- `conventions.json` — Adoption percentages
- `refactoring_needed_*.txt` — Non-conforming file list
- `debug_*.log` — Debug log **only on error** (never in normal operation)

## Limitations & Caveats

Record these in `CONVENTIONS.md`:
- **Extraction threshold**: The percentage used (default 90%).
- **Tool version / timestamp**: When extraction was performed.
- **Languages covered**: Which languages were scanned.
- **Files excluded**: From `.convention-ignore`.
- **Known limitations**: LLM-based extraction is a suggestion, not authoritative; always verify against actual code and tests.

## Best Practices

1. Always run discovery (`project-discovery`) before convention extraction to know which languages are present.
2. Never commit `config.yaml`, `.env`, or files containing API keys.
3. Run convention extraction as part of CI/CD if the repository supports it — but do not block builds on convention failures in MVP.
4. After extraction, review the generated conventions for accuracy before committing them.
5. If the external tool fails entirely, fall back to manual convention documentation from the project's existing patterns.
