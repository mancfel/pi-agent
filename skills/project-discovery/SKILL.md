---
name: project-discovery
description: Discovers repository structure, stack, modules, interfaces, dependencies, tests, conventions and analogous implementations; produces an inventory report following the template in references/templates.md.
---

# Project Discovery Skill (`project-discovery`)

Use this skill when you need to produce a comprehensive discovery report for a target repository. This is always the **first phase** of any feature development workflow (transition `NEW → INVESTIGATING`). All commands are executed directly by the agent in foreground.

## Execution Model — Single Agent, Foreground Only

> Run every command yourself inline. Do NOT delegate discovery to a sub-agent or background process.
>
> For each step:
> - Execute shell commands directly and parse results immediately.
> - Read discovered files fully before citing them.
> - Build the report incrementally as you go.
> - Report progress to the user after each major phase.

## Admitted Input States
- `NEW` — start fresh investigation
- `INVESTIGATING` — continue or refresh an existing investigation

If the current spec status is anything else, emit `STOP`: *"Discovery only admits states NEW or INVESTIGATING."*

## Prerequisites Check

Before starting, verify:
```bash
# Required tools
which python3   # or python on Windows
which rg        # ripgrep (preferred) OR which fd  # fd-find fallback
```

If `rg` and `fd` are both unavailable, document this in the report under "Limitations" and fall back to `find` / `dir` commands.

## Discovery Algorithm

Execute these phases sequentially in foreground.

### Phase Z: Check for Existing Documentation Files
Before scanning, check if `CONVENTIONS.md` or `ARCHITECTURE.md` already exist:
```bash
ls <repo-root>/CONVENTIONS.md   # exists → read and report contents
ls <repo-root>/ARCHITECTURE.md  # exists → read and report contents
```
If they do NOT exist, the discovery report MUST include explicit sections that can be used to **create** them. The output of this skill is the primary input for generating both files.

### Phase A: Repository Structure

### Phase A: Repository Structure
1. **Top-level tree**: Run `tree -L 2 --dirsfirst` (or equivalent `ls -R`) to capture directory structure.
2. **Total file count**: Count all `.py`, `.ts`, `.js`, `.rs`, `.go`, `.java`, etc. files.
3. **Languages detected**: Identify primary languages from extensions.

### Phase B: Entry Points & Modules
1. Search for common entry point patterns:
   ```bash
   rg -l "if __name__ == .main." *.py    # Python
   rg -l "export default|export async" src/*.ts src/*.tsx  # TypeScript/React
   rg -l "pub fn main" src/*.rs           # Rust
   find . -name "*.csproj" -o -name "*.sln" | head -20      # C#
   ```
2. For each entry point, read the file to understand its role and dependencies.

### Phase C: Dependencies
1. **Python**: Read `requirements.txt`, `setup.py`, `pyproject.toml`
2. **TypeScript/JS**: Read `package.json` (`dependencies`, `devDependencies`)
3. **Rust**: Read `Cargo.toml`
4. **Go**: Read `go.mod`
5. Summarize runtime vs. dev dependencies with purpose inferred from package name.

### Phase D: Test Structure
1. Find test directories/files:
   ```bash
   rg -l "test_|_test\.py|describe\(|it\(" tests/ spec/ __tests__/ 2>/dev/null
   find . -name "*test*" -o -name "*spec*" | grep -v node_modules | grep -v \.git
   ```
2. Identify the test framework used (pytest, jest, mocha, etc.) by reading config files or imports.

### Phase E: Conventions Detected
Scan for existing conventions in:
- `AGENTS.md`, `.editorconfig`, `.eslintrc*`, `.prettierrc`, `pyproject.toml`
- Naming patterns from file/directory names (`rg --files | head -50`)
- Error handling patterns (`raise Exception|throw new Error|Result::Err`)
- Documentation style (docstrings, JSDoc, comments)

### Phase G: Architecture Inference
Infer the project's architectural structure from discovered patterns:
1. **Module boundaries**: Identify logical groupings (e.g., controllers/services/repositories, feature folders).
2. **Dependency direction**: Trace imports/uses between modules — which module depends on which.
3. **Data flow**: How does data enter (API entry points) and exit (DB, external APIs)?
4. **Deployment model**: Is it monolith, microservices, serverless? Check for Dockerfiles, k8s manifests, CI configs.
5. Record findings in a structured format suitable for populating `ARCHITECTURE.md`.

### Phase F: Analogous Implementations
When a specific feature/pattern is requested as search anchor:
1. Use `rg` to find the pattern across the codebase.
2. Read 2–3 representative files fully.
3. Record key symbols and assess reuse signal (HIGH / MEDIUM / LOW).

## Output

Produce a discovery report using the template in **references/templates.md**. Save it at:
```
<REPO_ROOT>/.agent/discovery-report-YYYYMMDD-HHmmss.md
```

### Documentation Generation Readiness
The output MUST contain structured data that can be used to create `CONVENTIONS.md` and `ARCHITECTURE.md` if they do not already exist. Specifically include:

| Section | Source Phases | Purpose |
|---------|--------------|--------|
| Conventions detected (Phase E) | Phase E → `CONVENTIONS.md` content | Naming, error handling, code style, anti-patterns |
| Architecture inference (Phase G) | Phase G → `ARCHITECTURE.md` content | Module boundaries, dependency graph, deployment model |
- If the files **already exist**, report their contents verbatim in a dedicated section so downstream skills can reference them instead of re-scanning.

### Always include (from original template):
- Date of scan
- Scope summary (file count, languages)
- Directory structure tree
- Entry points with descriptions
- Dependencies table
- Test framework & locations
- Conventions detected
- Architecture inference (module boundaries, dependency direction, data flow)
- Analogous implementations (if search anchor was provided)
- Notes & caveats (tool limitations, unreadable files, etc.)

## Fallbacks
| Tool | Fallback Command | Notes |
| ---- | ---------------- | ----- |
| `rg` | `find . -name "*.py" -exec grep -l "pattern" {} \;` | Slower, less precise regex support |
| `fd` | `find . -type f -name "*.ts"` | More verbose output |
| `tree` | `ls -R | head -100` | Flat listing only, no tree structure |

## Best Practices
- Always read a file **completely** before citing its contents. Never infer from filenames alone.
- Use relative paths in the report (relative to repository root).
- If the repository is large (>50k files), limit scanning depth and document the truncation.
- Do not modify any source files — discovery is read-only.
