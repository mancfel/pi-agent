---
name: feature-review
description: Reviews spec artifacts against project rules, conventions, and patterns; produces a traceability-verifiable verdict. Blocks approval on FAIL.
---

# Feature Review Skill (`feature-review`)

Use this skill to review feature specification artifacts before they can transition from `PLAN_READY` to `APPROVED`. This is the **gate** between planning and implementation — no code changes may begin without a passing review. All review checks are performed directly by the agent in foreground.

## Execution Model — Single Agent, Foreground Only

> Perform every checklist item yourself inline. Do NOT delegate review to a sub-agent or background process.
>
> For each check:
> - Open and read the actual files being reviewed (requirements.md, design.md, tasks.md).
> - Run grep/rg commands yourself against source files to verify citations.
> - Build the verdict incrementally as you complete each checklist category.
> - Write the final review verdict file immediately after completing all checks.

## Admitted Input States
- `PLAN_READY` — only features in PLAN_READY state are eligible for review
- `DESIGNED` — allow early review of design-only artifacts

If incoming state is anything else, emit: `"STOP: Review only admits states PLAN_READY or DESIGNED."`

## Feature Name Resolution

Before starting the review, determine the `<feature-name>`:
1. If explicitly provided by the user, use it directly.
2. If not clear (e.g., "review that feature"), ask the user which feature to review.
3. Look for existing spec files under `specs/<candidate-name>/` or `.pi/plans/<candidate-name>.md`.
4. If multiple candidates exist, list them and ask the user to pick one.

### Artifact Paths to Read
| File | Full Path | Purpose |
| ---- | --------- | ------- |
| Requirements | `specs/<feature-name>/requirements.md` | Acceptance criteria, EARS format |
| Design | `specs/<feature-name>/design.md` | Architectural decisions, data flow |
| Tasks | `specs/<feature-name>/tasks.md` | Atomic task checklist with traceability |
| Existing review (if any) | `specs/<feature-name>/review.md` | Previous verdict for context |

For compact plans: `.pi/plans/<feature-name>.md`.

## Review Checklist

For each item below, verify against actual source files (open them, do not infer):

### 1. Precedent Verification
| Check | How to Verify | Pass Criteria |
| ----- | ------------- | ------------- |
| ≥2 precedents cited | Read each cited file; confirm it exists and contains relevant patterns | Every precedent resolves to an existing file with matching symbols |
| Justification if <2 | If fewer than two, check for documented reason in requirements.md | Justification is present and reasonable |

### 2. Requirements Quality
| Check | How to Verify | Pass Criteria |
| ----- | ------------- | ------------- |
| EARS syntax used | Scan acceptance criteria for WHEN/THEN/SHALL keywords | All ACs use proper EARS phrasing |
| Testable criteria | Each criterion describes a verifiable behavior | No vague criteria like "improve performance" without metrics |
| In-scope clarity | Out of scope section exists and lists items | Clear boundaries defined |

### 3. Design Completeness
| Check | How to Verify | Pass Criteria |
| ----- | ------------- | ------------- |
| Decisions documented | design.md has Architectural Decisions section with options considered | At least one decision per significant choice |
| Data flow described | Flowchart or text description present | Input → Processing → Output chain clear |
| File changes enumerated | Table listing all files to be modified/added/deleted | Every changed file mapped in requirements context |

### 4. Convention & Architecture Alignment
> **Pre-condition**: Read `CONVENTIONS.md` and `ARCHITECTURE.md` from repository root if they exist (AGENTS.md § Pre-Planning & Implementation Context Check).

| Check | How to Verify | Pass Criteria |
| ----- | ------------- | ------------- |
| AGENTS.md rules checked | Compare proposed changes against project's AGENTS.md sections | No violations of naming, error handling, library preferences |
| CONVENTIONS.md consulted | Cross-reference generated conventions with design choices | Design respects existing code style and patterns |
| .agent/patterns.md followed | Review proposed patterns against documented anti-patterns | No use of flagged anti-patterns |
| ARCHITECTURE.md boundaries respected | Verify file changes stay within declared module boundaries; dependencies follow allowed direction | No cross-boundary violations or forbidden imports |

### 5. Traceability Matrix
Verify that every requirement maps to test scenarios and tasks:

```markdown
REQ-1 → AC-1 → TEST-X → TASK-002
PROP-2 → INVARIANT-Y → PROPTEST-Z → TASK-003
```

If any requirement has no linked task or test, flag as a gap.

### 6. State & Artifact Integrity
| Check | How to Verify | Pass Criteria |
| ----- | ------------- | ------------- |
| Frontmatter `status:` present | YAML frontmatter in all spec files | status field is valid enum value |
| Date fields consistent | created_date ≤ updated_date | Both dates present and valid YYYY-MM-DD |
| Tags present | tags: [...] in frontmatter | At least [spec] tag present |

## Verdict Output Location

Produce the verdict at one of these locations (choose based on artifact structure):
- **`specs/<feature-name>/review.md`** — standalone review document (preferred for full specs), OR
- **Append as section to `design.md`**: `# Review Verdict`

For compact plans, append to `.pi/plans/<feature-name>.md`.

### PASS Verdict Template
```markdown
---
name: feature-review
description: Reviews spec artifacts against project rules, conventions, and patterns; produces a traceability-verifiable verdict. Blocks approval on FAIL.
---

# Review Verdict — {{FEATURE_NAME}}

## Date
{{DATE}}

## Status: ✅ PASS

All checks passed. The spec is ready for user approval.

## Summary
| Category | Result | Notes |
| -------- | ------ | ----- |
| Precedents | ✅ | 2 cited, both verified |
| Requirements (EARS) | ✅ | All criteria testable |
| Design Decisions | ✅ | Options documented |
| Convention Conformity | ✅ | No AGENTS.md violations |
| Traceability | ✅ | Every requirement linked to task and test |
| Artifact Integrity | ✅ | Frontmatter valid |

## Verified References
- `{{FILE_PATH_1}}` — confirmed symbol(s): `{{SYMBOLS}}`
- `{{FILE_PATH_2}}` — confirmed pattern matches design approach

## Approval Recommendation
This feature spec may proceed to APPROVED status upon user confirmation.
```

### FAIL Verdict Template
```markdown
# Review Verdict — {{FEATURE_NAME}}

## Date
{{DATE}}

## Status: ❌ FAIL

The following gaps must be addressed before approval:

## Gaps
| # | Category | Issue | Required Action | Severity |
| - | -------- | ----- | --------------- | -------- |
| 1 | Precedents | Only 1 precedent cited, no justification added | Add second precedent or document why none exist | HIGH |
| 2 | Traceability | REQ-3 has no linked task in tasks.md | Create TASK mapping to REQ-3 | MEDIUM |
| 3 | Convention | Proposed naming conflicts with AGENTS.md section on identifiers | Rename {{CLASS}} per AGENTS.md convention | HIGH |

## Blocked Transitions
- ❌ Cannot transition to APPROVED — gaps listed above must be resolved first.
```

### Post-Review Action
After writing the verdict, take one of two paths:

**PASS** → Recommend `APPROVED` transition. Wait for user confirmation before advancing.

**FAIL** → Report gaps to the user and **return to revision mode**. The agent should help the user fix each gap by updating the relevant spec artifact(s). Do NOT attempt to implement code to "fix" a review finding — that is a plan revision task, not an implementation task.

> **Common mistake**: After a review FAIL, the agent starts writing code to address findings. This is wrong. Review findings are about spec quality (missing precedents, unclear requirements, broken traceability), not about feature implementation. All fixes go into spec files first, then re-review.

## Blocking Conditions (Automatic FAIL)

The review MUST fail if any of these are detected:
1. No precedents cited AND no justification documented.
2. Acceptance criteria missing EARS keywords entirely.
3. Design proposes changes to files not identified in requirements context.
4. Task checklist is empty or contains only vague items ("implement feature").
5. Violation of `AGENTS.md` rules (naming, error handling, preferred libraries).
6. Proposed use of anti-patterns from `.agent/patterns.md`.
7. Missing or invalid YAML frontmatter in spec files.

## Best Practices

1. **Read source files**: Do not verify citations by grep alone — open each file and read the relevant sections.
2. **Be specific about gaps**: Each gap must include the exact location (file:line), what's wrong, and how to fix it.
3. **Severity levels**: HIGH = blocks approval; MEDIUM = should be fixed but may proceed with user awareness; LOW = nice-to-have improvement.
4. **Persist the verdict**: Always write review.md (or Review Verdict section) — never just report verbally.
5. **No auto-approval**: Even a perfect review only recommends APPROVED — the user must confirm explicitly.
