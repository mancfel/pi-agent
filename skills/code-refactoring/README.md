# Code Refactoring Skill — Quick Reference

## Purpose

Orchestrates **minimal-changes code refactoring** in target repositories. Identifies only necessary changes to reach a user-defined target state, with zero breaking behavior unless explicitly agreed.

## When to Use

- "Clean up this file/module" → use `code-refactoring` (not feature-development)
- "Extract validation logic from controller" → yes
- "Fix performance bottleneck" → yes
- "Add new API endpoint" → NO; use `feature-development` instead
- "Refactor database layer to support new query pattern" → yes

## Quick Start

```bash
# 1. Invoke the skill via pi-agent prompt:
#    "Use code-refactoring skill on [target repo] to [describe target state]"

# 2. The agent will follow these phases:
#    NEW → INVESTIGATING → ANALYZED → PLANNED → APPROVED → IMPLEMENTING → VERIFY → DONE

# 3. Artifacts created under:
#    specs/<refactor-name>/requirements.md   ← What changes + why
#    specs/<refactor-name>/design.md         ← Before/after comparison
#    specs/<refactor-name>/tasks.md          ← Atomic task list with regression checks
#    specs/<refactor-name>/analysis.md       ← Dependency map & risk assessment
```

## Key Differences from `feature-development`

| Aspect | feature-development | code-refactoring |
|--------|---------------------|------------------|
| Goal | Add new functionality | Transform existing code |
| Tests | May add new tests | Never modify existing tests without consent |
| Breaking changes | Anticipated (new APIs) | Forbidden unless explicitly agreed |
| Planning phase | Zero code changes | Zero code changes + working tree must be clean |
| Verification | New behavior correctness | **Regression** — old behavior preserved exactly |
| Minimum principle | N/A | Core constraint: only change what's strictly necessary |

## Critical Guardrails

1. **No test modifications** without explicit user agreement
2. **Ask before deciding** on any ambiguity or conflicting approach
3. **Read-before-write**: Every edit preceded by a fresh file read
4. **Zero code during planning**: Working tree verified clean before APPROVED state
5. **All tests must pass** after refactoring; regression = stop and re-plan

## Scripts

- `scripts/refactor_analyze.py` — Dependency graph extraction, symbol reference scanning, breaking-risk estimation
  - Usage: `python refactor_analyze.py --target-dir <path> [--symbol NAME] [--language py|cs]`
