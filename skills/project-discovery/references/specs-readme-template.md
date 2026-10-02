# Specs Index — {{REPOSITORY_NAME}}

This directory tracks all feature specification artifacts for this repository. Each feature has its own subdirectory with a full spec (requirements, design, tasks) or, for small changes, a compact plan at `.pi/plans/<feature>.md`.

## Features

| Feature | Status | Created | Last Updated | Files | Link |
| ------- | ------ | ------- | ------------ | ----- | ---- |
| mage-build-system | PLAN_READY | 2026-09-03 | 2026-09-03 | requirements.md, design.md, tasks.md | [tasks](mage-build-system/tasks.md) |
| authentication-middleware | APPROVED | 2026-08-15 | 2026-08-20 | requirements.md, design.md, tasks.md | [tasks](authentication-middleware/tasks.md) |

## Status Legend

| Symbol | State | Meaning |
| ------ | ----- | ------- |
| 🆕 | `NEW` | Feature request received |
| 🔍 | `INVESTIGATING` | Discovery and research in progress |
| 📐 | `DESIGNED` | Design document created |
| ✅ | `PLAN_READY` | Full spec ready for review |
| 👍 | `APPROVED` | Approved by user; implementation pending |
| ⚙️ | `IMPLEMENTING` | Code changes in progress |
| 🧪 | `TESTING` | Tests running / verification phase |
| 🔎 | `REVIEW` | Post-implementation review |
| ✔️ | `DONE` | Feature completed |

## Usage

Each feature subdirectory contains:
- **requirements.md** — User story, acceptance criteria (EARS format), correctness properties
- **design.md** — Architectural decisions, data flow, file/class change plan
- **tasks.md** — Atomic task checklist with `[ ]`/`[x]` tracking and requirement traceability
- **review.md** (optional) — Review verdict from `feature-review` skill
- **implementation-log.md** (optional) — Deviations, conflicts, new patterns during implementation
