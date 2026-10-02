---
name: feature-implement
description: Executes approved feature implementation sequentially from task checklist. Checks that status is APPROVED before starting, updates [ ] to [x] after each milestone, writes implementation-log.md for complex features, and reverts to PLAN_READY on design conflict.
---

# Feature Implementation Skill (`feature-implement`)

Use this skill to execute the implementation of an **approved** feature specification. This is the **Implement → Verify** phase of `feature-development`. All work is performed directly by the agent in foreground.

## Execution Model — Single Agent, Foreground Only

> Execute every task yourself inline. Do NOT spawn implementer sub-agents or background workers.
>
> For each task:
> - Read context files fully before making changes.
> - Apply edits directly and verify them immediately.
> - Update the checklist `[ ] → [x]` after completing each task.
> - If a conflict arises, stop immediately and report it to the user.

## Admitted Input States
- `APPROVED` — ready to begin implementation
- `IMPLEMENTING` — continue or resume implementation
- `PLAN_READY` — only when reopening due to a discovered conflict

If incoming state is anything else, emit: `"STOP: Implementation only admits states APPROVED, IMPLEMENTING, or PLAN_READY (reopening)."`, unless user explicitly overrides with confirmation message.

## Feature Name Resolution

Before starting implementation, determine `<feature-name>`:
1. If the orchestrator passed it explicitly, use it directly.
2. If not provided, ask the user which feature's tasks should be implemented.
3. Look for spec files under `specs/<candidate>/tasks.md` or `.pi/plans/<candidate>.md`.
4. If multiple candidates exist, list them and ask the user to select one.

### Artifact Paths Expected
| File | Full Path | Purpose |
| ---- | --------- | ------- |
| Tasks checklist | `specs/<feature-name>/tasks.md` | Atomic task list with `[ ]`/`[x]` tracking |
| Requirements (for context) | `specs/<feature-name>/requirements.md` | Acceptance criteria being validated |
| Design (for context) | `specs/<feature-name>/design.md` | Architectural decisions to follow |
| Test plan (for reference) | `specs/<feature-name>/test-plan.md` | Detailed test scenarios, mock strategies, configuration snippets |
| Existing review verdict | `specs/<feature-name>/review.md` | Previous review state, if any |
| Implementation log | `specs/<feature-name>/implementation-log.md` | Created on first deviation or for complex features |

For compact plans: `.pi/plans/<feature-name>.md`.

## Pre-Implementation Artifact Integrity Check (CRITICAL)
> Before executing any scaffolding or initialization task that might conflict with existing files.

1. **Verify spec artifact tree is intact**: Confirm all core artifacts exist at their expected paths:
   ```bash
   ls specs/<feature-name>/requirements.md  # MUST exist
   ls specs/<feature-name>/design.md        # MUST exist
   ls specs/<feature-name>/tasks.md         # MUST exist
   ```
2. If ANY file is missing → STOP and report to user. Do NOT proceed with implementation on a broken state.
3. **Check for reference data preservation**: List non-source files in the repo root (`.xml`, `.pdf`, `.csv`, etc.) — these are project context assets that must not be deleted during scaffolding.

## Pre-Implementation Context Loading (Mandatory)

**Before executing ANY implementation task**, the agent MUST read existing project documentation to ensure alignment with established conventions and architecture.

1. **Verify spec artifacts still present** (re-check after any scaffolding operation): run the integrity check from above again.
2. **Check for `CONVENTIONS.md`** in repository root — if exists, read full content.
3. **Check for `ARCHITECTURE.md`** in repository root — if exists, read full content.
3. Identify rules that apply to files being modified or created:
   - Naming conventions for classes/methods/variables
   - Error handling patterns
   - Module boundaries and dependency direction
   - Library preferences and anti-patterns
4. If a proposed change conflicts with an existing convention or architectural rule → STOP and ask user approval before proceeding.
5. This step is separate from (and comes before) the status verification below.

## Pre-Implementation Check

Before executing any task:

1. **Verify status**: Read the spec file's frontmatter. Status MUST be `APPROVED`.
   ```yaml
   ---
   status: APPROVED
   updated_date: 2026-09-03
   tags: [spec, tasks]
   ---
   ```
2. If status is NOT `APPROVED`:
   - For `PLAN_READY` → emit STOP and suggest re-review.
   - For any other state → emit STOP with explanation of valid transitions.
3. Confirm target repository root path one final time before making changes.

## Implementation Algorithm

### Step 1: Parse Task Checklist
Read the task checklist from `tasks.md` (or compact plan). Extract all unchecked `[ ]` tasks in order.

```markdown
- [ ] **TASK-001**: {{description}} — REQ-N, TEST-M
- [x] **TASK-002**: {{description}} — REQ-K (already completed)
```

Only process tasks marked `[ ]`. Skip already-completed `[x]` tasks.

### Step 2: Execute Tasks Sequentially
For each task:

1. **Read context files** listed in the task's "Precedents" or "File Changes" references.
2. **Implement changes** following the design document and using cited precedents as patterns.
3. **Verify locally** that the change is consistent with the requirement it validates.
4. **Update checklist**: Change `[ ]` to `[x]` for the completed task.
5. **Log the completion** (for complex features, write to `implementation-log.md`).

### Step 3: Handle Design Conflicts

If during implementation a conflict with the approved design is discovered:

1. **Stop immediately**. Do not proceed with further tasks.
2. **Document the conflict** in both the task's description and `implementation-log.md`:
   ```markdown
   ## Conflict Log
   | Date | Task | Conflict Description | Resolution Needed |
   | ---- | ---- | -------------------- | ----------------- |
   | YYYY-MM-DD | TASK-00X | {{DESCRIPTION}} | Re-review required |
   ```
3. **Revert status**: Change frontmatter from current state to `PLAN_READY`.
4. **Report to user**: Explain what was found, why it conflicts, and that re-review is needed.

### Step 3.5: Read Test Plan (Optional but Recommended)
Before implementation begins, check for `specs/<feature-name>/test-plan.md`. If it exists:
- Review the detailed test case breakdown to understand expected behavior.
- Note any mock strategies or configuration requirements (e.g., jsdom polyfills).
- Use this as a checklist during verification — ensure each listed scenario is covered by an actual test file.

### Step 4: Verification (Post-Implementation)

After all tasks are marked `[x]`:

1. Run the test suite if available:
   ```bash
   pytest tests/        # Python
   npm test             # TypeScript/JS
   cargo test           # Rust
   dotnet test          # C#
   ```
2. If tests pass → update status to `TESTING` then `REVIEW`.
3. If tests fail → document failures in implementation-log.md and report to user. Do NOT auto-fix without user confirmation.

## Implementation Log Template (`specs/<feature-name>/implementation-log.md`)

Create this file when the feature touches ≥3 files or involves multiple phases:

```markdown
# Implementation Log — {{FEATURE_NAME}}

## Session History
| Date | Task | Status | Notes |
| ---- | ---- | ------ | ----- |
| YYYY-MM-DD | TASK-001 | ✅ Completed | Implemented as per design; no deviations. |
| YYYY-MM-DD | TASK-002 | ⚠️ Conflict | Discovered that existing API does not support required signature. Reverted to PLAN_READY for re-review. |

## New Patterns Observed
> Document patterns discovered during implementation that were not in the original plan but proven by code.

- Pattern A: `{{FILE_PATH}}` uses {{PATTERN_DESC}} — validated by test {{TEST_NAME}}

## Deviations from Plan
| Task | Planned | Actual | Reason |
| ---- | ------- | ------ | ------ |
| TASK-XXX | {{PLAN}} | {{ACTUAL}} | {{REASON}} |

```

## Knowledge Update (Post-MVP Suggestion)

After successful implementation, **propose** updates to `.agent/`:
1. Read existing `.agent/patterns.md`.
2. If new patterns emerged, draft an addition with references to actual file(s) and symbol(s).
3. Do NOT apply automatically — present the proposed update for user approval.
4. Similarly, create ADR entries in `.agent/decisions/` only for cross-component decisions made during implementation.

## Best Practices

1. **Sequential execution**: Never execute tasks out of order or in parallel unless they are explicitly independent (documented as such in tasks.md).
2. **One task at a time**: Complete each task fully before moving to the next. Verify checklist update after each completion.
3. **No silent changes**: Every modification must be traceable to a specific requirement and task. If you find something that needs changing but is not in any task, stop and report it.
4. **Preserve existing tests**: Do not modify passing tests without explicit justification linked to a requirement.
5. **Immutable spec artifacts**: NEVER delete, move, rename, or overwrite files under `specs/<feature-name>/`. This is the highest-priority prohibition — more important than any scaffolding convenience.
6. **Safe project initialization**: When running `create-next-app`, `npm init`, or similar against an existing repo:
   - Always use `--force` / `-f` flags to avoid file conflict prompts
   - If no force flag exists: manually create scaffolded files one-by-one instead of using the tool
   - Never move spec/reference data into a temporary directory and then forget to restore it
7. **Git-friendly commits conceptually**: Each completed task should represent a coherent change that could be committed independently.
6. **Windows compatibility**: Use proper path separators; verify file operations work on Windows paths (backslashes).

## State Transition Summary

| Action | From → To | Condition |
| ------ | --------- | --------- |
| Start implementation | APPROVED → IMPLEMENTING | Status was APPROVED |
| Continue tasks | IMPLEMENTING → IMPLEMENTING | Tasks remain unchecked |
| Design conflict discovered | IMPLEMENTING → PLAN_READY | Conflict documented in log |
| All tasks done, tests pass | TESTING → REVIEW | Verification passed |
| Review complete | REVIEW → DONE | User confirms completion |
