---
name: feature-development
description: Orchestrates MVP feature development workflow — Understand, Find precedents, Design, Plan, Test Plan, Approval, Implement, Verify, Knowledge update. Reads/updates status frontmatter and applies STOP rule before implementation. Acts as entry point for any new feature request.
---

# Feature Development Skill (`feature-development`)

Use this skill as the **orchestration entry point** for any new feature request in a target repository. In the MVP it orchestrates the full workflow using the patterns defined in each specialized skill's instructions — all work is executed directly by the agent, not delegated to background sub-agents.

## Admitted Input States
- `NEW` — fresh feature request
- Any state where user has explicitly requested re-evaluation of an existing feature
- **`PLAN_READY` with revision request**: When the user asks to modify requirements, design, or tasks (not implement them)

If no spec file exists yet, create one with `status: NEW`. If one exists, verify that the incoming state transition is permitted per the state machine defined in **feature-planning/references/agents-extension.md**:

```
NEW → INVESTIGATING → DESIGNED → PLAN_READY → APPROVED → IMPLEMENTING → TESTING → REVIEW → DONE
PLAN_READY → PLAN_READY    (revision loop — user requests plan changes)
IMPLEMENTING → PLAN_READY  (reopening on conflict)
APPROVED → PLAN_READY      (user rejects approval and asks for revisions first)
```

On invalid transition: emit `STOP` with explanation and halt.

## Feature Name Resolution

Before starting any phase, resolve the feature name:

1. If the user provided a clear, unique name in their initial request or subsequent message, use it.
2. If no name was given, or the requested name is ambiguous (e.g., "fix bug", "improve something"), **ask the user** for a short descriptive name using kebab-case format.
3. Store the resolved name as `<feature-name>` and derive all artifact paths from it:
   - Full spec root: `specs/<feature-name>/`
   - Compact plan path: `.pi/plans/<feature-name>.md`
4. Confirm the resolved name with the user before proceeding to planning if it was inferred rather than explicitly stated.

## Execution Model — Single Agent, Foreground Only

> **All work must be executed directly by the agent in foreground. Do NOT spawn background sub-agents.**
>
> In MVP mode:
> - Every phase is performed step-by-step by the single calling agent.
> - If a specialized skill's pattern applies, follow its instructions inline rather than delegating.
> - For example: instead of "delegate to project-discovery", run discovery commands yourself following the algorithm in that skill.
> - Instead of spawning a `reviewer` sub-agent, perform the review checklist yourself using feature-review's criteria.
> - The orchestrator reads/writes state files and coordinates phases; it does not offload work to other agents or threads.

## Workflow Phases

The skill performs these phases sequentially (following each skill's inline instructions). **Every phase must respect the AGENTS.md rules** — read files before writing, and always check for `CONVENTIONS.md` / `ARCHITECTURE.md` before planning or implementing.

### Phase 0: Context Loading & Artifact Integrity Check (Pre-Work)
> **This is mandatory. No work begins until this step completes.**

Before any other phase starts, the agent MUST:

1. **Check for existing project documentation** in the repository root:
   ```bash
   ls <repo-root>/CONVENTIONS.md      # if exists → READ FULL FILE
   ls <repo-root>/ARCHITECTURE.md     # if exists → READ FULL FILE
   ```
2. If either file exists, read it completely and store its content in context. Identify rules that apply to the current feature scope.
3. If neither file exists, delegate to `project-discovery` skill (Phase 2) which will create them during discovery. Do NOT proceed to planning until conventions/architecture are known.
4. **Do not skip this step** — even if you think you "know" the project from a previous session. Always re-read because snapshots may be stale.
5. **Verify spec artifact integrity**: If `specs/<feature-name>/` exists (from a prior planning cycle), confirm all core artifacts are present:
   ```bash
   ls specs/<feature-name>/requirements.md  # MUST exist
   ls specs/<feature-name>/design.md        # MUST exist
   ls specs/<feature-name>/tasks.md         # MUST exist
   ```
   If any file is missing, STOP and report to user before proceeding. Never attempt to recover deleted files — ask user whether to regenerate from memory or abort.

### Phase 1: Understand
- Parse the user's feature request.
- Identify target repository root path.
- Resolve the feature name (ask user if unclear).
- Determine if an existing spec file should be updated or a new one created.
- Set initial status to `INVESTIGATING`.

### Phase 2: Find Precedents — Execute project-discovery pattern directly
Run discovery commands yourself following the algorithm in **project-discovery/SKILL.md**:
- Scan directory structure, entry points, dependencies, tests, conventions.
- Use results to identify analogous implementations, relevant files, symbols, and patterns.
- Record at least two precedent references (or document justification for fewer).

### Phase 3: Convention Extraction — Execute convention-extractor pattern directly
If the feature touches code conventions (naming, structure, error handling):
- Run the wrapper script or invoke extraction logic inline per **convention-extractor/SKILL.md**.
- Generate or update `CONVENTIONS.md` using `--merge` flag if an existing file is present.
- Include extraction metadata in the convention output.

### Phase 4: Design & Plan — Execute feature-planning pattern directly
With the resolved `<feature-name>`:
- Create artifacts under `specs/<feature-name>/` (full spec) or `.pi/plans/<feature-name>.md` (compact plan).
- Follow each step of **feature-planning/SKILL.md**: precedent search, requirements, design, tasks generation.
- Ensure all templates from **references/templates.md** are followed.
- Set status to `PLAN_READY` upon completion.

### Phase 4b: Revision Loop (Plan Feedback)
> This phase handles requests for changes to spec artifacts while in `PLAN_READY` state. It runs **between** Phase 4 (Design & Plan) and Phase 5 (Test Planning), and can repeat any number of times before approval.

When the user asks to "change", "modify", "revise", or "update" any part of an existing plan (requirements, design, or tasks):

1. **Do NOT invoke `feature-implement`.** The agent must remain in planning mode.
2. Read the relevant spec file(s): `requirements.md`, `design.md`, or `tasks.md`.
3. Apply the requested changes to the artifact(s).
   - Update frontmatter: set `updated_date` to today's date; keep status as `PLAN_READY`.
   - If requirements changed → re-check traceability matrix and update task links if needed.
   - If design changed → verify data flow diagram still matches decisions.
4. After each revision round:
   - Report what was changed, referencing specific sections/lines.
   - Ask the user: "Should I proceed to test planning (Phase 5), approval gate (Phase 6), or do you need further revisions?"
5. Only when the user confirms "approve", "proceed", or equivalent — transition to Phase 5.

**Guardrail**: If a revision request would require code changes that are not reflected in any spec artifact, ask the user first whether they want to: (a) update the plan with the change, then implement; or (b) skip planning and go straight to implementation (not recommended for MVP features).

### Phase 5: Test Planning (New Artifact Creation)
> This phase creates a standalone `test-plan.md` artifact **before** approval. It is optional for trivial features but mandatory when the feature touches ≥2 logical layers (e.g., API routes + UI components) or introduces new business logic.

When triggered (automatically during planning review or explicitly requested by user):

1. **Scan the codebase** for all testable units:
   - Utility functions (`lib/utils.ts`, custom helpers)
   - Pure aggregation/computation functions (`lib/aggregators.ts`, etc.)
   - UI components (`components/*.tsx`) — both pure rendering and interactive widgets
   - API route handlers (`app/api/**/route.ts`) — focus on data transformation, not HTTP plumbing
   - Type definitions / constants reference files

2. **Decide testing stack** with the user before creating artifacts:
   | Decision | Options |
   |----------||
   | Test runner | Vitest (recommended for Next.js/Vite), Jest (larger ecosystem) |
   | Component test library | React Testing Library + @testing-library/user-event |
   | Mock strategy | Direct function mocks via `vi.mock()` (preferred), MSW (full HTTP interception) |
   | File structure | Co-located (`components/X.test.tsx`) or grouped by layer (`tests/unit/`, `tests/components/`, `tests/routes/`) |

3. **Create `test-plan.md`** under `specs/<feature-name>/` following this structure:
   ```yaml
   ---
   status: PLAN_READY
   created_date: YYYY-MM-DD
   updated_date: YYYY-MM-DD
   tags: [spec, tests]
   feature_name: <name>
   related_specs: [requirements.md, design.md, tasks.md]
   ---
   ```

4. **Required sections in test-plan.md:**
   - **Scope & Strategy**: Table mapping layers → files → coverage target → approach
   - **File Structure**: Directory tree of all test files to be created (mirrors production layout)
   - **Test Cases — Detailed Breakdown**: For each component/function:
     - Component name + expected test count
     - Key scenarios as bullet points (rendering assertions, user interactions, edge cases)
     - Note which tests require `user-event` vs pure RTL rendering
   - **Mock Strategy**: How external dependencies are stubbed (e.g., `vi.mock('@/lib/azure-tables')`)
   - **Configuration Snippets**: vitest.config.ts and tests/setup.ts content if new setup needed
   - **Dependencies to Add**: New dev-only packages required for testing
   - **Execution Commands**: npm scripts for running tests

5. **Link from tasks.md**: Each task in `tasks.md` should reference relevant test files:
   ```markdown
   | # | Task | Depends On | Description | Verification | Status |
   |---|------|-----------|-------------|--------------|--------|
   | T1.1 | ... | — | ... | See `tests/unit/utils.test.ts`, `tests/components/SummaryCards.test.tsx` | `[ ]` |
   ```

6. **After creation**, update the spec status to `PLAN_READY` and ask user: "Test plan created at `specs/<feature-name>/test-plan.md`. Should I proceed to approval gate (Phase 6), or do you need further revisions?"

### Phase 6: Approval Gate
- No implementation may begin until status is `APPROVED`.
- Status can only be set to `APPROVED` on explicit user confirmation after a successful review.
- If not approved, halt and report current state to user.

### Phase 7: Implement — Execute feature-implement pattern directly
When status is `APPROVED`:
- Read tasks from `specs/<feature-name>/tasks.md` (or compact plan).
- Follow each step of **feature-implement/SKILL.md**: verify status, execute tasks sequentially, update `[ ] → [x]`, handle conflicts.
- On design conflict during implementation: revert status to `PLAN_READY`, log the conflict in `implementation-log.md`, and halt.

### Phase 8: Verify
- After implementation, verify that all test scenarios pass.
- Update status to `TESTING` then `REVIEW` upon verification.

### Phase 9: Knowledge Update
- If new patterns were discovered, propose updates to `.agent/patterns.md` or create ADRs in `.agent/decisions/`.
- Updates are **proposed for approval**, not applied automatically.
- Set final status to `DONE`.

## Revision vs Implementation Signal

When the agent receives any request while in `PLAN_READY` or `DESIGNED` state, it must classify intent:

| User says... | Intent Classification | Action |
| --- | --- | --- |
| "change X", "modify Y", "update Z" (referring to plan content) | **Revision** — stay in planning mode | Update relevant spec artifact(s), keep status `PLAN_READY` |
| "fix something discovered during review" | **Revision** — update plan first | Apply changes to specs, ask for re-review if needed |
| "implement this feature", "start coding", "go ahead with implementation" | **Implementation** — proceed to Phase 7 | Verify status is `APPROVED`, invoke implement logic |
| "apply the fix directly" (bypassing plan) | **Escalation** — confirm before bypassing | Ask user: "Do you want to update the plan first or skip straight to code?" |

If intent is unclear, **always default to revision mode** when in `PLAN_READY` state. Never assume a change request means "also implement it."

## State Management

Each spec file uses YAML frontmatter with a `status:` field. The skill reads this at phase boundaries:

```yaml
---
status: PLAN_READY          # Current state
created_date: 2026-09-03
updated_date: 2026-09-03    # Updated on every change
tags: [spec, tasks]
---
```

### Update Pattern
When transitioning states, update only the `status` and `updated_date` fields:

```python
# Before transition
frontmatter["status"] = new_status
frontmatter["updated_date"] = today()
```

## Artifact Paths Reference

| Format | Path Pattern | Example |
| ------ | ------------ | ------- |
| Full spec root | `specs/<feature-name>/` | `specs/mage-build-system/` |
| Requirements | `specs/<feature-name>/requirements.md` | `specs/mage-build-system/requirements.md` |
| Design | `specs/<feature-name>/design.md` | `specs/mage-build-system/design.md` |
| Tasks | `specs/<feature-name>/tasks.md` | `specs/mage-build-system/tasks.md` |
| Test plan (optional) | `specs/<feature-name>/test-plan.md` | `specs/budget-tracker-webapp/test-plan.md` |
| Review verdict (optional) | `specs/<feature-name>/review.md` | `specs/mage-build-system/review.md` |
| Implementation log (optional) | `specs/<feature-name>/implementation-log.md` | `specs/mage-build-system/implementation-log.md` |
| Compact plan | `.pi/plans/<feature-name>.md` | `.pi/plans/auth-fix.md` |

## STOP Rule

Before any implementation phase begins:
1. Verify status is exactly `APPROVED`.
2. If not `APPROVED`, emit:
   ```
   STOP: Implementation requires status APPROVED. Current status: {current_status}.
   No changes will be made until user confirms approval.
   ```
3. Do NOT attempt to auto-approve or bypass this check.

## Repository Root Resolution

The skill operates relative to a repository root path provided by the user or inferred from context. All file paths in specs are **relative** to this root. The agent must always confirm the target repository before starting work.

## Immutable Spec Artifacts — PROHIBITED OPERATIONS
> During ANY phase of feature development (especially Phase 7: Implementation), the following operations are **STRICTLY PROHIBITED**:

1. **DELETE, MOVE, RENAME, or OVERWRITE** any file under `specs/<feature-name>/` directory tree
2. **DELETE, MOVE, or REMOVE** any reference data files that were part of the original repository root before scaffolding (e.g., `.xml`, `.pdf`, `.csv` source exports)
3. **Use temporary directories at root level** for operations like `create-next-app` without first verifying all critical artifacts are preserved outside the target scope
4. **Never delete a backup after operation completes** — always verify restoration succeeds before cleaning up any temp directory
5. If scaffolding tool blocks on existing files: use alternative approach (`--force` flag if available, manual initialization from template) rather than deleting user content

## Safe Scaffolding Protocol
When initializing a project framework (`npx create-next-app`, `npm init`, etc.) and the repo already contains spec/reference data:
1. Check whether `specs/<feature-name>/` exists → it must be preserved in place
2. Use `--force` / `-f` flags to overwrite only conflicting scaffolded files (e.g., `app/page.tsx`, `.gitignore`) without touching other directories
3. If no force option exists: manually initialize by creating each scaffold file individually instead of running the scaffolder against an existing directory
4. After scaffolding completes, verify all three core artifacts still exist under `specs/<feature-name>/`

## Best Practices

1. **Single agent, foreground only**: Every phase is executed directly by this skill's instructions. No sub-agents, no background threads, no delegation to external processes.
2. **One feature at a time**: Do not interleave multiple features' spec files.
3. **Ask for name if unclear**: Never guess a feature name — prompt the user when the request is ambiguous.
4. **Document every deviation**: If implementation deviates from the approved plan, record it in `implementation-log.md` and revert status to `PLAN_READY`. Apply immutable artifact rules above before any scaffolding or initialization step.
5. **Precedents over assumptions**: Always cite actual existing implementations rather than inferring patterns from names alone.
6. **Git-aware**: Use `git log`, `git blame`, `git show` for evolutionary context when available.
7. **Respect wiki skills**: No interference with `wiki-ingest.ts` or other wiki-related functionality.
8. **Windows compatibility**: All file paths must use forward slashes or proper Windows escaping; verify with PowerShell commands if on Windows.
