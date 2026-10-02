# Agent Operating Guidelines

This file contains rules governing how agents behave during code generation, editing, and script usage.

## File Read-Before-Write Rule (Critical)

**Before modifying any file — whether via `edit`, `write`, or inline tool commands — the agent MUST read the full current content of the target file first.** This rule exists to prevent overwriting user edits made outside of agent sessions, changes from other agents, or concurrent modifications.

### Procedure
1. **Read the entire file** into context before applying any edit.
2. Use the latest content as the baseline for your `oldText` match strings in `edit` operations.
3. If a file has been modified by another party since the last session, your cached/stale version will not match and the edit will fail — this is correct behavior; re-read and retry.
4. After completing multi-step edits on the same file, read it again before starting new changes (do not rely on an earlier snapshot).
5. When editing files that are frequently user-modified (e.g., source code files, configuration), always verify no unexpected drift exists between what you intend to change and the current state.

### Why This Matters
- Agents work with **stale snapshots** of files from previous sessions or tool calls.
- Users may have manually edited a file while the agent was busy elsewhere.
- Another agent session may have modified the same file concurrently.
- Applying edits against a stale `oldText` silently reverts unrelated changes.

### Enforcement
- Every edit operation must be preceded by at least one `read` call for the target file within the same turn or immediately before.
- If a user reports that their changes were reverted, check whether a read was performed; if not, this is a protocol violation and must be corrected.

---

## Pre-Planning & Implementation Context Check (Critical)

**Before planning any code change or beginning implementation, the agent MUST check for and read existing project documentation files.** These files encode accumulated knowledge about the repository that must be respected to avoid conflicts with established patterns.

### Required Files to Check
The agent must look for these files in the **repository root** before starting work:

| File | Purpose |
|------|--------|
| `CONVENTIONS.md` | Project coding conventions: naming, error handling, structure, library preferences, anti-patterns |
| `ARCHITECTURE.md` | High-level architecture: module boundaries, data flow, dependency graph, deployment model |

If either file exists (check common locations: repo root, `.pi/`, or any project-specific documentation directory), the agent MUST:
1. **Read the full content** of each existing file.
2. **Identify relevant sections** that apply to the current task scope (e.g., if modifying a controller, check convention rules for controllers).
3. **Align all proposed changes** with what these documents prescribe — do not introduce patterns that contradict them without explicit user approval and document update.
4. If no such files exist yet, create them during discovery (delegate to `project-discovery` skill) before proceeding to planning or implementation.

### When This Applies
This rule triggers whenever the agent is about to:
- Generate new code files or modify existing ones.
- Create or update spec artifacts (`requirements.md`, `design.md`, `tasks.md`).
- Execute any feature development phase (planning, design, implementation).

### Why This Matters
- CONVENTIONS.md captures **community/team agreements** on style and structure — ignoring it creates drift from established norms.
- ARCHITECTURE.md documents **structural decisions** — violating module boundaries causes architectural decay.
- Agents work with project context from scratch; these files are the only persistent memory of accumulated knowledge across sessions.

### Enforcement
- If either file exists but was not read before code generation/editing, this is a protocol violation.
- When proposing changes that would conflict with an existing convention or architecture rule, explicitly flag the conflict and ask user approval rather than silently overriding.

---

# Python Script Library Management Instructions

This document defines the guidelines that agents must follow when generating or using Python scripts within the project.

## Python Script Workflow

When an agent needs to generate or execute a Python script to perform an operation — whether explicitly requested by the user or autonomously determined by the model as necessary instead of creating a temporary inline script — it must strictly follow these steps:

1. **Preliminary check**:
   - Before writing a new script, the agent must determine whether the task is related to the execution of a skill requested by the user.
   - If a skill is involved, the agent must check the `scripts/` folder and `skill.md` inside that skill's directory (`skills/<skill-name>/`). Otherwise, the agent must check the global `scripts/` folder and `scripts/index.md`.
   - If the corresponding folder or index/documentation file does not exist yet, the agent must create them.
   - The agent must examine the index to check if a script useful for performing the task is already present.

2. **Case A: Existing script found**
   - If a suitable script is found, the agent must **execute** the existing script.
   - If necessary, the agent must **extend** the existing script to support the new use case.
   - The agent must update the script description inside `scripts/index.md` or `skill.md` to reflect the newly added features.

3. **Case B: No suitable script found**
   - If no suitable script exists, the agent must **create a new Python script** (saving it in the skill's `scripts/` folder if the user requested the execution of a skill, or otherwise in the global `scripts/` folder), designing it to be as **generic and reusable** as possible.
   - The agent must use the new script to perform the requested task.
   - The agent must add the new script to `scripts/index.md` or `skill.md`, including:
     - The script file name.
     - Instructions on how to use it (arguments, parameters, examples).
     - A detailed description of the features offered.

## Script Locations
	- **projectRoot\agent\scripts**
	- **~\.pi\agent\skills\<skill>\scripts**
	- **~\.pi\agent\scripts**