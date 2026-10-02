---
name: feature-planning
description: Creates complete, traceable spec artifacts (requirements.md, design.md, tasks.md or compact plan) from templates in references/templates.md. Searches for at least two precedents using rg/fd with documented fallback. Sets status to PLAN_READY upon completion.
---

# Feature Planning Skill (`feature-planning`)

Use this skill when a feature request has been understood and discovery/convention extraction are complete, and you need to produce the full specification artifacts. This is the **Design → Plan** phase of `feature-development`. All work is performed directly by the agent in foreground.

## Execution Model — Single Agent, Foreground Only

> Execute every step yourself inline. Do NOT delegate planning or precedent search to sub-agents.
>
> For each step:
> - Run `rg`/`fd` commands yourself and parse results immediately.
> - Read cited files fully before referencing them.
> - Write spec artifacts directly using templates from references/templates.md.
> - Report progress after completing each major section (requirements, design, tasks).

## Admitted Input States
- `INVESTIGATING` — starting planning after discovery
- `DESIGNED` — continuing from an existing partial design
- `PLAN_READY` — refreshing or updating an existing plan (no regression)

If incoming state is anything else, emit: `"STOP: Planning only admits states INVESTIGATING, DESIGNED, or PLAN_READY."`

## Feature Name Resolution

Before creating any spec artifact, determine the feature name:

1. If the user explicitly provided a clear, unique name in their request, use it directly.
2. If no name was given, or the requested name is ambiguous (e.g., "fix bug", "add something"), **ask the user** for a short descriptive name (kebab-case preferred).
3. The canonical path for full specs is `specs/<feature-name>/` relative to the repository root.
4. For compact plans the path remains `.pi/plans/<feature-name>.md`.

### Examples of Good Names
- `mage-build-system`
- `authentication-middleware`
- `control-plane-health-endpoints`

### Bad / Ambiguous Names (prompt user)
- `improve performance` → ask: "What specific component should be improved?"
- `bug fix` → ask: "Which feature or file needs fixing?"

## Compact vs Full Spec Decision

Before creating artifacts, determine which format applies based on scope and complexity:

### Use Compact Format (`.pi/plans/<feature-name>.md`) if ALL are true:
1. Feature touches at most 3 files (existing or new).
2. No new modules, packages, or top-level directories introduced.
3. No cross-component decisions required.

### Use Full Spec (`specs/<feature-name>/`) otherwise:
- Create folder `specs/<feature-name>/` in the repository root.
- Generate `requirements.md`, `design.md`, and `tasks.md` inside it using templates from **references/templates.md**.

## Planning Algorithm

> **AGENTS.md Rule**: Before any step below, read `CONVENTIONS.md` and `ARCHITECTURE.md` from the repository root if they exist (see AGENTS.md § Pre-Planning & Implementation Context Check).

### Step 0: Load Project Context — Read CONVENTIONS.md / ARCHITECTURE.md
Before generating any spec artifact, check for and load existing project documentation:

1. Look in the repository root for `CONVENTIONS.md` and `ARCHITECTURE.md`.
2. If either exists → **read full content** into context immediately.
3. Identify which sections apply to the current feature scope (e.g., naming rules for controllers, module boundaries for data flow).
4. If neither file exists → STOP and delegate to `project-discovery` skill first. Do NOT begin planning without knowing conventions or architecture.
5. Reference these documents explicitly when writing requirements, design decisions, and tasks — cite specific convention/article numbers or architectural constraints by name.

### Step 1: Ensure Specs Directory Exists
For full specs, create the directory structure:
```bash
mkdir -p specs/<feature-name>
# Also ensure specs/README.md exists (create if missing)
```

The `specs/README.md` should contain a table of all tracked features with their status:
| Feature | Status | Created | Last Updated | Files |
| ------- | ------ | ------- | ------------ | ----- |
| [mage-build-system](mage-build-system/tasks.md) | PLAN_READY | YYYY-MM-DD | YYYY-MM-DD | requirements.md, design.md, tasks.md |

### Step 1: Repository Context Discovery
Use the results from `project-discovery` to identify:
- Entry points relevant to this feature
- Dependencies that may be affected
- Test framework and location
- Existing conventions

If discovery was not run first, execute it now (delegate to project-discovery skill).

### Step 2: Precedent Search (Minimum Two)
Search for analogous implementations using `rg`/`fd`:

```bash
# Example searches — adapt anchor terms to the specific feature
rg "pattern_anchor" --type py -l | head -20   # Python files
rg "symbol_name" --ts -l                       # TypeScript files
find . -name "*test*" -path "*/tests/*"        # Related tests
```

For each precedent found:
1. Read the file **completely** before citing it.
2. Record the file path, key symbols/classes/functions, and what it does well / should be avoided.
3. If fewer than two precedents exist, document the justification explicitly in `requirements.md`.

### Step 3: Git Context (When Useful)
Enrich findings with git history:

```bash
git log --oneline -20 -- <relevant_file>    # Recent commits affecting relevant code
git blame -L start_line,end_line <file>      # Who last changed a specific section
git show <commit_hash>:<path>                # See how a file looked at a specific point
```

Use this to understand evolutionary patterns — not as authoritative source, but for context.

### Step 4: Generate Requirements (`specs/<feature-name>/requirements.md`)
Using the template from **references/templates.md**:
- Write user story in standard format.
- Include Context & Existing Patterns section with ≥2 precedents.
- List related files and symbols in a table.
- Write acceptance criteria using EARS syntax (WHEN/THEN/SHALL).
- Define correctness properties based on examples or property-based testing where applicable.
- Document risks and mitigations.

### Step 5: Generate Design (`specs/<feature-name>/design.md`)
Using the template from **references/templates.md**:
- Describe architectural decisions with options considered.
- Include data flow diagram (mermaid or text fallback).
- List file/class changes in a table.
- Define test strategy linking requirements to test methods.

### Step 5.5: (Optional) Generate Test Plan (`specs/<feature-name>/test-plan.md`)
If the feature touches ≥2 logical layers (e.g., API routes + UI components, or introduces new business logic), create a standalone `test-plan.md` artifact after generating tasks but before setting status to `PLAN_READY`. This is NOT part of the standard template — it follows the pattern documented in **feature-development/SKILL.md § Phase 5b**.

Key decisions to make:
1. Select test runner (Vitest recommended for Next.js/Vite projects; Jest for larger codebases).
2. Determine file structure: co-located tests vs grouped by layer (`tests/unit/`, `tests/components/`, `tests/routes/`).
3. Plan mock strategy for external dependencies — prefer direct function mocks via `vi.mock()` over HTTP-level interception when possible, as they are faster and more reliable.
4. If the project lacks a testing infrastructure, include required configuration snippets (`vitest.config.ts`, `tests/setup.ts`) in the plan.
5. If pure business logic exists inside API routes (aggregation, filtering), extract it into separate files (`lib/aggregators.ts`, etc.) to enable unit testable functions.

### Step 6: Generate Tasks (`specs/<feature-name>/tasks.md` or compact plan)
Using the template from **references/templates.md**:
- Break implementation into atomic tasks grouped by phase.
- Each task must link back to validating requirement(s) and test(s).
- Reference specific test file paths from `test-plan.md` where applicable (e.g., "See `tests/unit/utils.test.ts").
- Use `[ ]` checklist format for persistent tracking.
- Include an Implementation Log section for recording deviations.

For compact plans, write `.pi/plans/<feature-name>.md`.

### Step 7: Set Status & Update Index
After all artifacts are created/updated:

1. Set `status: PLAN_READY` in each spec file's frontmatter:

```yaml
---
status: PLAN_READY
created_date: {{TODAY}}
updated_date: {{TODAY}}
tags: [spec]
---
```

2. Update (or create) `specs/README.md` with the new feature entry.

## EARS Syntax Reference

Use these keywords in acceptance criteria:

| Keyword | Meaning | Example |
| ------- | ------- | ------- |
| WHEN | Trigger condition | WHEN the user submits an empty form |
| THE | System response to trigger | THE system SHALL display a validation error |
| IF | Conditional precondition | IF the file exists AND is readable |
| SHALL | Mandatory requirement | The system SHALL log all errors |
| SHALL NOT | Prohibition | The system SHALL NOT expose stack traces to users |

## Correctness Properties

Define properties that must hold after implementation:

- **Invariant**: A condition always true (e.g., "A processed message SHALL never be reprocessed").
- **Example-based**: Given specific inputs, verify expected outputs (useful when invariants are hard to define).
- **Property-based**: When applicable, note where property-based tests could validate the behavior.

Link each property to specific requirements using `PROP-<N>` identifiers.

## Best Practices

1. **Verify before citing**: Always read a file completely — do not cite from filenames or grep snippets alone.
2. **Two precedents minimum**: If you cannot find two analogous implementations, document why and proceed with reduced precedent support.
3. **Atomic tasks**: Each task should be completable in a single editing session without introducing partial state.
4. **Traceability matrix**: Every requirement maps to ≥1 test scenario; every task maps back to ≥1 requirement.
5. **Mermaid fallback**: If the target viewer does not render mermaid diagrams, provide text-based flow descriptions.
6. **No credentials**: Never include API keys, config values, or secrets in spec artifacts.

### Mermaid Diagram Safety Rules

When generating mermaid diagrams (flowcharts, sequence diagrams, etc.), strictly follow these rules to avoid parse errors:

#### Node Labels — What NOT to Use
- ❌ HTML `<br/>`, `</br>`, or `<br>` tags inside node labels
  - ✅ Use `(line break)` via parentheses: `[Node A\nLine B]` with literal backslash-n
  - ✅ Or split into multiple nodes connected by arrows
- ❌ **Nested square brackets** like `I[IArchitectureDetector[]]` — this is the #1 cause of parse errors.
  Mermaid uses `[...]` for node definitions, so inner `[]` terminates the label prematurely.
  - ✅ Remove the `[]` from the label entirely (context makes it clear): `I[IArchitectureDetector]`
  - ✅ Replace `[]` with `<>` or parens inside the label: `I["IArchitectureDetector<T>"]`
  - ✅ Quote the full label and use `< >`: `I["IArchitectureDetector&lt;T&gt;"]`
- ❌ Unescaped `{`, `}`, `[`, `]` inside text content of any node type
  - ✅ Wrap the entire label in double quotes: `A["Label with {braces}"]`
  - ✅ Or use round/ellipse shapes which are more forgiving: `A("text")`
- ❌ Raw angle brackets `<tag>` / `</tag>` — Mermaid interprets these as HTML, but parsers vary
  - ✅ Use Unicode alternatives or descriptive text instead
- ❌ Leading/trailing whitespace in labels without quoting
  - ✅ Quote labels containing spaces at boundaries: `A[" starts with space"]`

#### Structure Rules
- Always declare nodes **before** referencing them in edges. Define `A[...]` before using `B --> A`.
- Avoid mixing subgraph indentation styles within the same diagram.
- Keep nested subgraphs to a maximum of two levels deep; deeper nesting increases parse fragility.
- Never use node IDs that conflict with reserved Mermaid keywords (e.g., `flow`, `subgraph`).

#### Edge Syntax — What NOT to Use
- ❌ Unlabeled conditional branches without explicit text: `B --> C` when you mean `B -->|label| C`
  - ✅ Include label if directionality matters for understanding: `B -->|yes| C` / `B -->|no| D`
- ❌ Mixed arrow types in the same flow without clear visual distinction
  - ✅ Stick to one edge style per logical section

#### Validation Checklist Before Writing a Diagram
Before embedding any mermaid block, mentally verify:
1. [ ] No HTML tags (`<br>`, `<span>`, etc.) inside node labels — use `(multi\nline)` or quotes instead.
2. [ ] **No nested square brackets** like `Node[SomeType[]]` or `Node<Generic<T>>[` — remove or replace inner `[]` with `< >`.
3. [ ] All special characters `{}`, `[`, `]` are quoted via double-quote wrapping: `["Label with []"]`
4. [ ] Every referenced node ID is defined earlier in the diagram.
5. [ ] Subgraph nesting ≤ 2 levels deep.
6. [ ] Labels do not start/end with unquoted whitespace.
7. [ ] Node IDs use only alphanumeric characters and underscores (no hyphens).
8. [ ] The diagram renders correctly as a single connected graph (not disconnected fragments, unless intentional).
