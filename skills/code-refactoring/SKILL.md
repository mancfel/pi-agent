---
name: code-refactoring

description: Orchestrates minimal-changes code refactoring — identifies required changes to reach a target state exposed by the user, proposes only necessary edits with zero breaking changes unless explicitly agreed, asks clarifying questions on ambiguity, prevents regressions, never modifies unit tests without consent, and applies all changes only after explicit green light following a strict INVESTIGATING → ANALYZED → PLANNED → APPROVED → IMPLEMENTING → VERIFY → DONE workflow.

---

# Code Refactoring Skill (`code-refactoring`)
Use this skill as the **orchestration entry point** for any code refactoring request in a target repository. Unlike feature-development (which adds new capabilities), this skill's mandate is to **transform existing code toward a target state using the minimum possible set of changes**, with zero breaking behavior unless explicitly agreed by the user.

## Core Principles (Non-Negotiable)
These principles govern every phase and decision:

| Principle | Description | Enforcement |
| --- | --- | --- |
| Minimum Changes | Only modify what is strictly necessary to reach the target state. Never refactor for its own sake. | Every proposed change must be traceable to a specific requirement or identified problem. |
| Zero Breaking Changes | Public API surface, external contracts, and observable behavior MUST remain unchanged unless the user explicitly agrees to break them. | The implementation plan MUST list all potentially breaking changes; each requires explicit [AGREED] marker from the user before proceeding. |
| Ask Before Deciding | When requirements are unclear, when analysis finds conflicting signals, or when multiple valid approaches exist — ask the user. Do NOT make disruptive decisions autonomously. | If any ambiguity exists in Phase 2 (Analysis), emit STOP with questions. Never guess intent. |
| Regression Prevention | Every refactoring must be validated against existing unit tests. No test may change without explicit user agreement. If a test breaks during verification, the refactoring is REJECTED until root cause is understood and resolved. | Tests pass → VERIFY phase. Test fails → IMPLEMENTING → PLANNED (revert to plan for re-review). |
| No Code Changes During Planning | The planning phase produces artifacts ONLY. Zero source files are modified until status reaches APPROVED. | Before entering APPROVED state, verify no working-tree changes exist in target repo. |
| Read-Before-Write | Before editing any file, read its full current content first. Never work from stale snapshots. | Every edit operation must be preceded by a fresh read of the target file. AGENTS.md rule enforced strictly. |

## Execution Model — Single Agent, Foreground Only

> All work is executed directly by the agent in foreground. Do NOT spawn background sub-agents or parallel workers.

>

> - Run analysis commands yourself and parse results immediately.

> - Read cited files fully before referencing them.

> - Write spec artifacts directly following this skill's templates.

> - Apply edits one at a time, reading each file before editing.

## Admitted Input States
- `NEW` — fresh refactoring request from user
- Any state where user has explicitly requested re-evaluation of an existing refactoring scope
If no spec file exists yet, create one with `status: NEW`. If one exists, verify that the incoming state transition is permitted per the state machine defined below:

```plaintext
NEW → INVESTIGATING → ANALYZED → PLANNED → APPROVED → IMPLEMENTING → VERIFY → DONE
PLANNED → PLANNED         (revision loop — user requests plan changes)
APPROVED → PLANNED        (user rejects approval and asks for revisions first)
IMPLEMENTING → PLANNED    (reopening on conflict or regression detected)
VERIFY → PLANNED          (regression found; revert to re-plan)

```
On invalid transition: emit `STOP` with explanation and halt.

## Feature Name Resolution
Before starting any phase, resolve the refactoring scope name:

1. If the user provided a clear, unique name in their initial request, use it.
2. If no name was given, or the requested name is ambiguous (e.g., "clean up", "fix some code"), **ask the user** for a short descriptive name using kebab-case format.
3. Store the resolved name as `<refactor-name>` and derive all artifact paths from it:

- Full spec root: `specs//`
- Compact plan path: `.pi/plans/.md`

1. Confirm the resolved name with the user before proceeding to planning if it was inferred rather than explicitly stated.

### Examples of Good Names
- `extract-validation-from-controller`
- `consolidate-duplicate-repositories`
- `replace-temp-variable-with-query`

### Bad / Ambiguous Names (prompt user)
- "clean up" → ask: "Which specific code or component should be cleaned?"
- "fix performance" → ask: "Which function or endpoint is the bottleneck?"
- "make better" → ask: "What target state do you want to reach?"

## Workflow Phases
The skill performs these phases sequentially. **Every phase must respect the AGENTS.md rules** — read files before writing, and always check for `CONVENTIONS.md` / `ARCHITECTURE.md` before planning or implementing.

---

### Phase 0: Context Loading & Scope Definition (Pre-Work)

> **This is mandatory. No work begins until this step completes.**

Before any other phase starts, the agent MUST:

1. **Check for existing project documentation** in the repository root:
   ```bash
         ls <repo-root>/CONVENTIONS.md      # if exists → READ FULL FILE
         ls <repo-root>/ARCHITECTURE.md     # if exists → READ FULL FILE

   ```
2. If either file exists, read it completely and store its content in context. Identify rules that apply to files being targeted by the refactoring scope.
3. If neither file exists, delegate to `project-discovery` skill which will create them during discovery. Do NOT proceed until conventions/architecture are known.
4. **Confirm target repository path** with the user before proceeding.
5. Parse the user's request into a clear **Target State Description**: what should the code look like after refactoring?

---

### Phase 1: Investigation (`NEW → INVESTIGATING`)
The agent investigates the current state of the code relative to the requested target state.

#### Step 1.1: Identify Scope Boundaries
- Determine which files, classes, methods, or modules are in scope based on the user's description.
- If boundaries are unclear, ask the user. Do NOT assume scope extends beyond what is explicitly described.

#### Step 1.2: Survey Current Code
For each file/module in scope:

1. Read the full content of every relevant source file.
2. Identify the **current problems** that motivate the refactoring (e.g., duplication, complexity, technical debt).
3. Document any existing conventions observed in the code under investigation.

#### Step 1.3: Exclude Auto-Generated Files (Mandatory)
Before scanning or analyzing any file, filter out auto-generated source code. Never plan refactoring against generated code — it will be overwritten by the next build/generation step.

**Files to exclude from ALL phases** (investigation, analysis, planning, implementation):

| Pattern | Examples | Generator |
| --- | --- | --- |
| .g.cs | GeneratedSerialization.cs, ServiceClient.g.cs | NSwag, OpenAPI CodeGen, T4 templates |
| Designer.cs | Form1.Designer.cs, MyControl.Designer.cs | Windows Forms Designer |
| .generated.cs / .gen.cs | Any file with .generated. or .gen. in name | Roslyn Source Generators, EF Core T4 |
| Files containing <auto-generated /> directive | Any file where the first lines contain this comment | All generators |
| obj/ and bin/ directories | Build output folders | MSBuild / dotnet CLI |
| /.g.cs (all depths) | Generated code deep in tree | Various source generators |

Implementation — always run these filters before any scan:

```bash
# Exclude generated files from rg/fd scans
rg --glob '!*.g.cs' --glob '!*Designer.cs' --glob '!*.gen.cs' 'pattern'
fd -t f -e cs --exclude '*.g.cs' --exclude '*Designer.cs' .

```
When using `refactor_analyze.py`, the script already skips `bin/` and `obj/`. If scanning C# projects, also add glob exclusions for `.g.cs` patterns.

#### Step 1.4: Map Dependencies (with Generated File Exclusions)
Use `rg`/`fd` with auto-generated file exclusions:

```bash
# Exclude .g.cs, Designer.cs, *.generated.cs from scans
rg --glob '!*.g.cs' --glob '!*Designer.cs' 'TargetSymbol'

```
Find all references to symbols being considered for change. Build a dependency map showing which developer-authored files import/call/extend the target symbols.

```bash
# Example: Find all usages of a symbol
rg "TargetMethodName" --type cs -l | head -50
rg "class TargetClass" --ts -l

```

#### Step 1.5: Identify Change Opportunities
For each identified problem, determine what specific changes** would address it:*

- *What code blocks need modification?*
- *What method signatures might change?*
- *Are there new abstractions needed (interfaces, base classes)?*
- *Can existing patterns in the codebase be leveraged?*

#### *Step 1.6: Set Status & Report*
*Set status to *`INVESTIGATING`* and produce an initial investigation summary. Ask the user: *"Does this scope cover everything you intended?"* If not, refine before proceeding.*

---

### *Phase 2: Analysis (*`INVESTIGATING → ANALYZED`*)*
*This is the core analytical phase where the agent determines ****exactly what changes are needed**** with minimum impact.*

#### *Step 2.1: Change Impact Assessment*
*For each identified change opportunity:*

| Change Type | Breaking Risk | User Consent Needed? |
| --- | --- | --- |
| Private method rename / internal refactor | None (private only) | No — but document in plan |
| Protected method signature change | Low-Medium | Yes — check inheritors first |
| Public API parameter removal/change | High | Yes — explicitly agreed [AGREED] |
| Public API return type change | High | Yes — explicitly agreed [AGREED] |
| Interface method addition/removal | Medium-High | Yes — check all implementors |
| New class/module creation (no existing refs) | None | No — but must be justified |

#### *Step 2.2: Minimum-Changes Verification*
*Before finalizing the analysis, apply this checklist to every proposed change:*

1. ***Is this change strictly necessary?**** If removing it still achieves the target state → reject the change.*
2. ***Can the same result be achieved with fewer changes?**** Consider alternative approaches and compare change counts.*
3. ***Does any change affect more files than needed?**** Scope each change to only the minimum set of files.*
4. ***Are there existing patterns in the codebase that achieve the same goal?**** Prefer reusing established patterns over introducing new ones.*
*If multiple valid approaches exist, present them to the user with a comparison table and ask for direction. Do NOT choose autonomously.*

#### *Step 2.3: Filter Out Auto-Generated Symbols from Analysis*
*When building the analysis report, exclude any symbol that is defined exclusively in auto-generated files (as per Phase 1 exclusion rules). If a symbol has definitions both in generated and developer-authored files, include it but mark which definition(s) are safe to refactor.*

#### *Step 2.4: Regression Risk Analysis*
*For every proposed change:*

1. *Identify all unit tests that exercise the affected code paths.*
2. *Determine whether each test would pass/fail after the refactoring (predictive analysis).*
3. *Flag any tests whose assertions might break due to changed behavior or output formatting.*
4. *If any test is predicted to fail → ****STOP**** and discuss with user. Document which tests are at risk and why.*

#### *Step 2.5: Ambiguity & Conflict Resolution*
*If during analysis you encounter:*

- *Unclear intent in the target state description → ask the user specific questions*
- *Conflicting requirements (e.g., "simplify but keep all current options") → present trade-offs and ask for priority*
- *Code that appears intentionally complex (may have hidden business logic) → flag as *`CAUTION`* and recommend manual review*
- *Dependencies on external systems whose behavior cannot be verified statically → mark as *`UNKNOWN`* and ask user to verify*
***Never proceed past Phase 2 with unresolved ambiguities.**** Report every open question to the user before transitioning to PLANNED.*

#### *Step 2.6: Set Status & Transition*
*Set status to *`ANALYZED`*. Produce the analysis report following the template in *`references/output-template.md`*. ****Ensure no auto-generated file appears anywhere in the report.**** Present findings to the user and confirm: *"Are all identified changes correct? Are there any additional concerns?"* Only after confirmation, transition to Phase 3.*

---

### *Phase 3: Planning (*`ANALYZED → PLANNED`*)*
*Create a detailed implementation plan that specifies ****exact changes**** to be made — but do NOT modify any source files yet.*

#### *Step 3.1: Generate Requirements (*`specs/<refactor-name>/requirements.md`*)*
*Using the template from references/templates.md (adapted for refactoring):*

- *Describe the current state and the target state clearly.*
- *List each change as a requirement with traceability.*
- *Define correctness properties — what must remain unchanged after refactoring.*
*For refactoring-specific requirements, use this format:*

```markdown
### REQ-R01: {{DESCRIPTION}}
- **Current State**: {{WHAT_EXISTS_NOW}}
- **Target State**: {{WHAT_WILL_EXIST_AFTER}}
- **Why**: {{RATIONALE}}
- **Breaking Risk**: NONE / LOW / MEDIUM / HIGH
- **User Consent**: [AGREED] or [NOT_REQUIRED - internal only]
- **Test Impact**: Which tests are affected and why they will still pass

```

#### *Step 3.2: Generate Design (*`specs/<refactor-name>/design.md`*)*
*Using the template from references/templates.md (adapted for refactoring):*

- *Describe architectural decisions with options considered.*
- *Include a ****Before/After comparison**** diagram showing structural changes.*
- *List every file change in a table with exact line ranges where applicable.*
- *Define regression test strategy — how correctness is verified without modifying tests.*
*Refactoring-specific design additions:*

| Section | Content |
| --- | --- |
| Before/After Diagram | Mermaid or text showing class/method relationships before and after |
| Change Impact Table | For each file: lines changed, symbols affected, callers impacted |
| Regression Verification Plan | How existing tests validate that behavior is preserved |

#### *Step 3.3: Generate Tasks (*`specs/<refactor-name>/tasks.md`*)*
*Using the template from references/templates.md (adapted for refactoring):*

- *Break implementation into atomic tasks grouped by logical change set.*
- *Each task must link back to its validating requirement(s) and test scenario(s).*
- *Use *`[ ]`* checklist format for persistent tracking.*
- *Include a ****Regression Checkpoint**** section listing which tests should pass after all tasks complete.*
*Refactoring-specific task format:*

```markdown
### Phase N: {{CHANGE_SET_NAME}}
- [ ] **TASK-00X**: {{DESCRIPTION}} — REQ-R{{N}}, PROP-{{K}}
  - Files: `{{PATH1}}`, `{{PATH2}}` (lines ~{{LINE_START}}–{{LINE_END}})
  - Precedents: `{{FILE_PATH}}`, symbol(s): `{{SYMBOLS}}`
  - Regression check: Existing test `tests/test_{{MODULE}}::test_{{METHOD}}` MUST still pass
  - Description: {{STEP_BY_STEP_INSTRUCTIONS}}

```

#### *Step 3.4: Zero-Code-Change Verification*
*Before setting status to PLANNED, verify:*

1. *No source files have been modified since the investigation phase.*
2. *Working tree is clean in the target repository.*
3. *All artifacts are self-consistent (requirements map to tasks, tests map to requirements).*
*If any code has been accidentally modified → revert and notify user immediately.*

#### *Step 3.5: Set Status & Request Approval*
*Set status to *`PLANNED`*. Present the complete plan to the user with a clear summary of:*

- *Total number of changes proposed*
- *Number of breaking-change risks identified*
- *Total estimated scope (files touched, lines changed)*
- *Any open questions or cautions*
*Ask explicitly: *"Do you approve this plan? Shall I proceed with implementation?"* Only on explicit approval does the workflow advance.*

---

### *Phase 4: Implementation Gate (*`PLANNED → APPROVED`*)*
***CRITICAL GATE**** — If any source file has been modified since Phase 0, STOP immediately. This is a protocol violation that must be corrected before proceeding.*

*No implementation may begin until status is *`APPROVED`* via explicit user confirmation.*

***Approval Checklist**** — present each item and wait for user acknowledgment:*

1. *All requirements are understood and accepted.*
2. *No unapproved breaking changes exist in the plan.*
3. *The minimum-changes principle was followed — no unnecessary refactoring included.*
4. *Unit tests will NOT be modified unless explicitly agreed (verify against plan).*
5. *Every task has clear, actionable instructions.*
6. ***Auto-generated files excluded****: Verify that NO task references *`.g.cs`*, *`Designer.cs`, or any file with `<auto-generated />` directive.
If any item fails → revert to PLANNED with explanation. Do NOT proceed.

On approval: set status to `APPROVED`.

---

### Phase 5: Implementation (`APPROVED → IMPLEMENTING`)
Execute tasks sequentially from the approved plan. This is where code changes actually happen.

#### Step 5.1: Pre-Task Verification
Before executing each task:

1. **Read CONVENTIONS.md** in repository root — if exists, read full content and verify alignment.
2. **Read ARCHITECTURE.md** in repository root — if exists, read full content and verify no architectural boundary violations.
3. Read the spec's requirements.md and design.md for context on this specific task.

#### Step 5.2: Execute Tasks Sequentially — Fail-Fast Compilation Gate
For each task:

1. **Read target files**: For every file listed in the task, read its **full current content**. Never rely on a cached/stale snapshot. This is mandatory per AGENTS.md Read-Before-Write rule.
2. **Apply changes precisely**: Make only the edits specified by the task instructions. Do NOT add "nice-to-have" improvements that were not approved. If you discover an additional improvement while working, STOP and ask the user whether to include it (this would require plan update first).
3. **Verify immediately after edit**:

- Re-read the file to confirm edits applied correctly.
- Verify no unintended modifications exist in surrounding code.

1. **FAIL-FAST COMPILATION GATE — Mandatory after every single task**:Before marking any task as `[x]`, run a full project build. This is NOT optional. Compiling only at Phase 6 makes it impossible to identify which of N tasks broke the build.
   ```bash
         # C# / .NET — compile entire solution, skip restore for speed
         dotnet build --no-restore <solution_or_project> -v q

   ```
   If no `.sln`/`.csproj` exists (other language):
   ```bash
         # Python
         python -m py_compile <modified_file>
         pytest --co --collect-only <affected_test_dir>   # dry-run: catches import/syntax errors

         # TypeScript / JavaScript
         npx tsc --noEmit                              # type-check without emitting

         # Java
         mvn compile -q                               # quiet mode, fail on first error
         javac -d out $(find src -name '*.java')      # fallback for non-Maven projects

   ```
   **Build result handling**:| Result | Action || ------ | ------ || Build succeeds (exit code 0) | Task is valid. Proceed to Step 5 (`Update checklist`). || Build fails with warnings only | Check whether warnings are new or pre-existing: `git diff --no-index` against last known-good build output. If all warnings are pre-existing → proceed. If any warning is new → STOP, document in implementation-log.md, revert task edits and re-plan. || Build fails with errors | **FAIL-FAST TRIGGERED**. Do NOT proceed to the next task. Stop immediately on this task and first fix the code. |
2. **Update checklist**: Only after Step 4 passes successfully. Change `[ ]` to `[x]` for the completed task.
   ```markdown
         ## Session History
         | Date | Task | Status | Notes |
         | ---- | ---- | ------ | ----- |
         | YYYY-MM-DD | TASK-00X | ✅ Completed | Applied changes as per plan; no deviations. |

   ```

#### Step 5.3: Auto-Generated File Protection During Implementation
**Absolute rule**: Never edit an auto-generated file, even if it appears in a task's scope.

If a task references a generated file:

1. Stop and document which generated file was referenced.
2. Identify the developer-authored partial class / base class / interface that corresponds to this generated code.
3. Move all refactoring changes to the developer-authored file instead.
4. Log the substitution in implementation-log.md.
This applies regardless of whether the user requested the change — generated code is never safe to modify directly.

#### Step 5.4: Handle Design Conflicts
If during implementation a conflict with the approved design is discovered (e.g., the planned change would break something not visible in static analysis):

1. **Stop immediately**. Do not proceed with further tasks or any additional edits to source files.
2. **Document the conflict** in both the task's description and `implementation-log.md`:
   ```markdown
         ## Conflict Log
         | Date | Task | Conflict Description | Resolution Needed |
         | ---- | ---- | -------------------- | ----------------- |
         | YYYY-MM-DD | TASK-00X | {{DESCRIPTION}} | Re-review required |

   ```
3. **Revert status**: Change frontmatter from current state to `PLANNED`.
4. **Do NOT revert code changes already made** — document them, explain why they cannot proceed as planned, and ask user for direction (re-plan vs. alternative approach).

#### Step 5.5: Test Integrity During Implementation
This is a critical guardrail:

1. **DO NOT modify any existing unit test file.** Ever. Unless the plan explicitly includes a `[AGREED]` marker for that specific test change AND the task references it.
2. If you discover that an existing test would fail after your refactoring → STOP immediately on that task. Document in implementation-log.md. Do NOT fix or bypass the test. The refactoring may need to be re-planned.
3. If new tests are needed to validate behavior preservation, propose them as additional tasks in the plan (go back to Phase 3) rather than writing them directly during implementation.

---

### Phase 6: Verification (`IMPLEMENTING → VERIFY`)
After all tasks are marked `[x]`:

#### Step 6.1: Regression Test Execution
Run the full test suite for the affected modules:

```bash
# Python
pytest <affected_test_dir> -v

# C# / .NET
dotnet test <project_under_refactor> --no-restore -v n

# TypeScript/JS
npm test -- <test_pattern>

# General compilation check
python -m py_compile <files>   # or equivalent for project language

```

#### Step 6.2: Verify Correctness Properties
For each correctness property defined in requirements.md (PROP-N):

1. Confirm that the refactored code still satisfies it.
2. If a property cannot be verified statically, note this as a limitation and recommend manual verification.

#### Step 6.3: Assess Results
| Result | Action |
| --- | --- |
| All tests pass + all properties hold | Set status to VERIFY → proceed to Phase 7 |
| Some tests fail (not modified) | REGRESSION DETECTED — set status back to PLANNED, document which tests failed and why, ask user for direction |
| Compilation/build errors | Stop immediately, document error details, revert to IMPLEMENTING with conflict log |

---

### Phase 7: Completion (`VERIFY → DONE`)
1. Present a final summary to the user:

- What was changed (files, lines, symbols)
- How many changes were made vs. what was planned
- Test results (pass/fail counts)
- Any deviations from the approved plan

1. If there are deviations, explain them clearly and note that they should be added to the implementation-log.md for future reference.
2. Set status to `DONE`.
3. **Propose** updates to any project documentation (patterns, conventions, architecture notes). Do NOT apply automatically — present for approval.

---

## Revision vs Implementation Signal
When the agent receives any request while in `PLANNED` or `ANALYZED` state:

| User says... | Intent Classification | Action |
| --- | --- | --- |
| "change X", "modify Y", "update Z" (referring to plan content) | Revision — stay in planning mode | Update relevant spec artifact(s), keep status as current state |
| "fix something discovered during review" | Revision — update plan first | Apply changes to specs, ask for re-review if needed |
| "implement this refactoring", "start applying changes", "go ahead" | Implementation — proceed to Phase 5 | Verify status is APPROVED, invoke implement logic |
| "apply the fix directly" (bypassing plan) | Escalation — confirm before bypassing | Ask user: "Do you want to update the plan first or skip straight to code?" |

If intent is unclear, **always default to revision mode**. Never assume a change request means "also implement it."

---

## State Management
Each spec file uses YAML frontmatter with a `status:` field. The skill reads this at phase boundaries:

```yaml
---
status: PLANNED          # Current state
created_date: 2026-09-07
updated_date: 2026-09-07 # Updated on every change
tags: [spec, refactoring]
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
| --- | --- | --- |
| Full spec root | specs/<refactor-name>/ | specs/extract-validation-from-controller/ |
| Requirements (adaptation) | specs/<refactor-name>/requirements.md | specs/extract-validation-from-controller/requirements.md |
| Design (adaptation) | specs/<refactor-name>/design.md | specs/extract-validation-from-controller/design.md |
| Tasks (adaptation) | specs/<refactor-name>/tasks.md | specs/extract-validation-from-controller/tasks.md |
| Analysis report | specs/<refactor-name>/analysis.md | specs/extract-validation-from-controller/analysis.md |
| Review verdict (optional) | specs/<refactor-name>/review.md | specs/extract-validation-from-controller/review.md |
| Implementation log | specs/<refactor-name>/implementation-log.md | specs/extract-validation-from-controller/implementation-log.md |
| Compact plan | .pi/plans/<refactor-name>.md | .pi/plans/consolidate-repos.md |

---

### Pre-Implementation Enforcement (Bypass Prevention)
The following behaviors indicate an agent bypassed required gates. These MUST be detected and corrected:

| Violation | Detection Method | Required Correction |
| --- | --- | --- |
| Source files modified before APPROVED state | git diff --stat shows changes when status ≠ APPROVED/IMPLEMENTING | Revert all unauthorized edits; trace which phase was skipped |
| Implementation started without spec artifacts | No files under specs/<refactor-name>/ exist | Create full plan first; present for approval |
| Tests were modified without [AGREED] marker | Any .csproj test file or Test. / test_ has git diffs vs. approved baseline | Revert test changes; re-plan if tests need updating |

If any violation is detected:

1. **STOP ALL WORK**.
2. Report the exact violation to the user with evidence (git diff, missing files).
3. Revert unauthorized code changes.
4. Resume from the correct phase only after user acknowledgment.

### Implementation Gate STOP Rule
Before ANY implementation begins:

1. Verify status is exactly `APPROVED`.
2. If not `APPROVED`, emit:
   ```plaintext
         STOP: Implementation requires status APPROVED. Current status: {current_status}.
         No changes will be made until user confirms approval.

   ```
3. Do NOT attempt to auto-approve or bypass this check.
Additionally, before **every single file edit** during Phase 5 (Implementation):

```plaintext
STOP: Read-before-write rule — have I read the full current content of the target file?
If NO → READ NOW. Do NOT proceed with edits.

```

---

## Repository Root Resolution
The skill operates relative to a repository root path provided by the user or inferred from context. All file paths in specs are **relative** to this root. The agent must always confirm the target repository before starting work.

---

## Edge Cases & Special Handling
| Scenario | Handling Procedure |
| --- | --- |
| User request is too vague ("clean up the code") | Ask clarifying questions about specific files, symbols, or problems. Do not guess scope. |
| Multiple valid refactoring approaches exist | Present comparison table (changes count, risk level, complexity) and ask user to choose. |
| Refactoring would require changing a third-party wrapper / generated code | Flag as CAUTION — recommend manual review since auto-modification may be overwritten by generators. |
| Target code has no tests at all | Document this risk in analysis.md. Proceed with caution; add regression tests as a separate task if approved. |
| User requests breaking changes | Create a separate section in requirements.md listing each proposed break. Require explicit [AGREED] marker per item before including in plan. |
| Tests fail during verification despite correct refactoring | STOP. Do NOT modify tests. Analyze root cause: is the test wrong, or did we miss something? Revert to PLANNED for re-review. |
| Code style conventions conflict with minimum-changes goal | Follow existing conventions unless user explicitly waives them. Document any trade-off decision. |
| Generated file in task scope |

STOP — identify corresponding developer-authored partial/base/interface and move changes there. Log substitution. NEVER edit `.g.cs`, `Designer.cs`, or `<auto-generated />` files directly.

| Agent attempted implementation without plan/approval | Protocol violation. The skill enforces Phase 3→4→5 sequence. If this happened, the agent ignored required gates: create spec artifacts first, present for approval, then implement. Revert any unauthorized code changes.

---

## Best Practices
1. **Single agent, foreground only**: Every phase is executed directly by this skill's instructions. No sub-agents, no background threads.
2. **One refactoring at a time**: Do not interleave multiple refactorings' spec files or code changes.
3. **Ask for name if unclear**: Never guess a scope name — prompt the user when the request is ambiguous.
4. **Document every deviation**: If implementation deviates from the approved plan, record it in `implementation-log.md` and revert status to `PLANNED`.
5. **Minimum changes over elegance**: Resist the urge to "improve" beyond what was requested. Refactoring for its own sake introduces risk without delivering user value.
6. **Git-aware**: Use `git log`, `git blame`, `git show` for evolutionary context when available (e.g., understand why a seemingly odd pattern exists).
7. **Respect existing tests as ground truth**: Passing tests define correct behavior. The refactoring must preserve this behavior exactly.
8. **Windows compatibility**: All file paths must use forward slashes or proper Windows escaping; verify with PowerShell commands if on Windows.
9. **Read before every edit**: This is not optional. Every `edit` operation must be preceded by at least one fresh `read` of the target file within the same turn or immediately before. Stale snapshots cause silent data loss.
10. **Fail-fast compilation after each task**: Never accumulate N tasks' worth of changes and compile only once. Build after EVERY atomic task in Phase 5 to isolate failures to a single change set.
11. **Never touch auto-generated files**: `.g.cs`, Designer.cs, Source Generator output, T4 templates — these are ephemeral artifacts. Refactor only developer-authored code (partial classes, base classes, interfaces). If a task references generated code, redirect it to the source.

---

## Script Locations
When scripts are needed for analysis (e.g., dependency graph extraction, call-graph building), they should follow the Python Script Library Management Instructions from AGENTS.md:

- Primary location: `~/.pi/agent/skills/code-refactoring/scripts/`
- Global fallback: `~/.pi/agent/scripts/`
- Index documentation: `~/.pi/agent/skills/code-refactoring/references/index.md` (created if missing)