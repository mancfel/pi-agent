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

## Modular Conventions System (Critical)

Conventions are organized as a **modular topic-based system** rather than monolithic files. Each convention file covers one specific topic (language, framework, pattern, testing, etc.). The agent MUST discover, resolve, and apply conventions following this hierarchical protocol.

### File Structure

```
Global conventions:  ~/.pi/agent/conventions/
  ├── conventions.md          ← Index / entry point (REQUIRED — always read first)
  ├── general.md              ← General coding principles
  ├── dotnet.md               ← .NET/C# specific rules
  ├── react.md                ← React/TypeScript frontend rules
  ├── unit-test-dotnet.md     ← Unit testing in .NET
  ├── unit-test-react.md      ← Unit testing in React
  └── ...                     ← Any number of topic modules

Project conventions: <project-root>/conventions/   (optional override layer)
  ├── conventions.md          ← Project-specific index (overrides global if present)
  └── ...                     ← Topic overrides for this project only
```

### Resolution Order (Cascading Override)

For any given convention **topic**, the resolution follows a cascading lookup:

1. **Check project-level first**: `conventions/<topic>.md` in the repository root
2. **Fall back to global**: `~/.pi/agent/conventions/<topic>.md`
3. The most specific (nearest) file wins — project rules **override** global rules.
4. If a topic is defined at both levels, project content takes precedence; topics only present globally are still applied.

> ⚠️ The agent does NOT merge files line-by-line. It reads whichever version of each topic file exists (project or global). A project can selectively override any subset of topics while inheriting the rest unchanged from global.

### Agent Protocol: Discovering and Applying Conventions

Before planning or implementing any code change, the agent MUST follow these steps:

#### Step 1 — Locate the Index File
- Check if `conventions/conventions.md` exists in the **repository root**.
- If yes → read it as the active index.
- If no → fall back to reading `~/.pi/agent/conventions/conventions.md`.
- This index is the **single entry point**. Never guess which topic files exist.

#### Step 2 — Identify Relevant Topics
- Analyze the task at hand (language, framework, pattern, testing, architecture, etc.).
- Read the index file and identify all topics that are relevant to the current work.
- Examples:
  - Writing a C# controller → look for `dotnet`, `unit-test-dotnet`
  - Building a React component with tests → look for `react`, `unit-test-react`
  - General refactoring → read `general` first

#### Step 3 — Resolve Each Topic File
For every identified topic:
1. Check if `<topic>.md` exists in project's `conventions/` folder.
2. If yes → **read the project version** (it overrides global).
3. If no → read the global version from `~/.pi/agent/conventions/<topic>.md`.
4. Read and internalize all resolved topic files before proceeding.

#### Step 4 — Apply All Resolved Conventions
- Align ALL proposed changes with the combined set of resolved conventions.
- Do NOT introduce patterns that contradict any loaded convention without explicit user approval.
- If a convention is ambiguous or conflicts between topics, flag it to the user for resolution.

### When This Applies
This rule triggers whenever the agent is about to:
- Generate new code files or modify existing ones.
- Create or update spec artifacts (`requirements.md`, `design.md`, `tasks.md`).
- Execute any feature development phase (planning, design, implementation).

### Why This Matters
- Modular conventions allow **incremental growth** — add topic modules as needs arise without bloating a single file.
- Project-level overrides enable **per-project customization** while inheriting sensible defaults globally.
- The index-first approach ensures agents always know what topics exist and which apply to their task.

### Enforcement
- Failing to locate and read the conventions index before code generation/editing is a protocol violation.
- Applying project-specific topic files over global ones (when they exist) without following the resolution order is a protocol violation.
- When proposing changes that would conflict with any loaded convention, explicitly flag the conflict and ask user approval rather than silently overriding.

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