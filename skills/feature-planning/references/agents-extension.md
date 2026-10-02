# Feature Development Workflow — Contract Extension for `AGENTS.md`

Add this section to any repository's `AGENTS.md` to enable the feature development workflow.

## Feature Development Schema

### State Machine

Features progress through these states, tracked via YAML frontmatter `status:` field in spec files (`specs/<feature>/tasks.md`, `.pi/plans/<feature>.md`).

| State | Description | Transition From | Transition To |
| ----- | ----------- | --------------- | ------------- |
| `NEW` | Feature request received, no work started | Initial | `INVESTIGATING` |
| `INVESTIGATING` | Discovery and investigation phase active | `NEW` | `DESIGNED` |
| `DESIGNED` | Design document created, awaiting planning | `INVESTIGATING` | `PLAN_READY` |
| `PLAN_READY` | Full spec (requirements + design + tasks) complete, awaiting review | `DESIGNED` | `APPROVED` |
| `APPROVED` | Spec reviewed and approved by user; implementation may begin | `PLAN_READY` (user confirmation only) | `IMPLEMENTING` |
| `IMPLEMENTING` | Implementation in progress | `APPROVED` | `TESTING`, `PLAN_READY` |
| `TESTING` | Tests running / verification phase | `IMPLEMENTING` | `REVIEW` |
| `REVIEW` | Post-implementation review | `TESTING` | `DONE` |
| `DONE` | Feature completed, knowledge updated | `REVIEW` | — |

### Allowed Transitions
```
NEW → INVESTIGATING → DESIGNED → PLAN_READY → APPROVED → IMPLEMENTING → TESTING → REVIEW → DONE
```

**Reopening**: `IMPLEMENTING → PLAN_READY` is allowed when a conflict with the approved design is discovered during implementation. The agent must document the conflict in the implementation log and stop further changes until the plan is re-reviewed.

**Approval Gate**: Only the user (or explicit user confirmation) can set `status: APPROVED`. No skill may auto-approve a feature.

### State Enforcement Rule (MVP)

In the MVP, state enforcement is **documentary**, not runtime:
1. Each skill declares its admitted input states at the top of its instructions.
2. If an incoming state is not admitted, the skill MUST emit `STOP` with a message explaining why.
3. In post-MVP, this becomes enforced by a TypeScript extension (`development-workflow.ts`) that blocks invalid transitions at runtime.

### Artifact Paths

Full specs are organized under `specs/<feature-name>/`:

| File | Path Example | Purpose |
| ---- | ------------ | ------- |
| Requirements | `specs/<feature-name>/requirements.md` | User story + EARS acceptance criteria |
| Design | `specs/<feature-name>/design.md` | Architectural decisions + data flow |
| Tasks | `specs/<feature-name>/tasks.md` | Atomic task checklist with traceability |
| Review verdict (optional) | `specs/<feature-name>/review.md` | PASS/FAIL review outcome |
| Implementation log (optional) | `specs/<feature-name>/implementation-log.md` | Deviations, conflicts, new patterns |

Compact plans use `.pi/plans/<feature-name>.md`.

### Compact Plan Criterion

Use `.pi/plans/<feature-name>.md` **only** when ALL of the following are true:
- The feature touches at most 3 existing or new files.
- No new modules, packages, or top-level directories are introduced.
- No cross-component decisions are required (all changes stay within one module).

If any condition is violated, use the full `specs/<feature>/` format instead.

### Execution Model — Single Agent, Foreground Only (MVP)

In MVP mode all workflow phases are executed **directly by the single calling agent in foreground**.

- No sub-agents, background threads, or external orchestrators spawn workers.
- Each skill's instructions are followed inline: commands run directly, files read/written immediately.
- The `pi-subagents` extension may exist but is NOT used for feature development phases during MVP.
- In post-MVP, a TypeScript runtime extension (`development-workflow.ts`) can introduce specialized roles (`explorer`, `architect`, `implementer`, `reviewer`) via controlled delegation — but this requires explicit configuration and state enforcement.

> If you see "delegate to X" in any skill's description, interpret it as "follow the pattern defined by X and execute the steps yourself."

### Context Obsolescence

Mark context as obsolete and re-trigger discovery when:
- A new file is added to a directory that the spec claims contains no similar implementations.
- An existing symbol's signature changes in a way not reflected in the design.
- Dependencies are upgraded or downgraded across major versions.
- More than 7 days have passed since the last discovery scan and the repository has had commits.

```markdown
