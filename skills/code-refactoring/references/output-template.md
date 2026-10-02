---
status: ANALYZED
created_date: {{DATE}}
updated_date: {{DATE}}
tags: [analysis, refactoring]
---

# Analysis Report — {{REFACTOR_NAME}}

## Target State Description
{{CLEAR_DESCRIPTION_OF_WHAT_THE_CODE_SHOULD_LOOK_LIKE_AFTER_REFACTORING}}

## Current State Assessment

### Problem Summary
| # | Problem Description | File / Symbol | Severity (H/M/L) |
|---|--------------------|---------------|------------------|
| P-1 | {{DESCRIPTION}} | `{{FILE_PATH}}`, `{{SYMBOL}}` | H/M/L |

### Scope Boundaries
| Category | Items In Scope | Items Out of Scope | Justification for Exclusion |
| -------- | -------------- | ------------------ | --------------------------- |
| Files | `{{PATH_1}}`, `{{PATH_2}}` | `{{EXCLUDED_PATH}}` | {{REASON}} |
| Symbols | `{{CLASS_OR_METHOD}}` | N/A | — |

## Dependency Map

### Direct Dependencies (Symbols Being Changed)
| Symbol | Defined In | Referenced By | Change Type |
| ------ | ---------- | ------------- | ----------- |
| `{{SYMBOL_NAME}}` | `{{FILE}}` | `{{REFERENCING_FILE}}` | rename / signature_change / remove / extract |

### Transitive Dependencies
> Document symbols that depend on the above, even indirectly.

- `{{TRANSITIVE_SYMBOL}}` → calls `{{DIRECT_SYMBOL}}` via {{INTERMEDIATE_PATH}}

## Proposed Changes

### C-01: {{CHANGE_TITLE}}
- **Problem Addressed**: P-{{N}}
- **Current Code** (file `{{PATH}}`, lines ~{{LINE_START}}–{{LINE_END}}):
  ```language
  {{BEFORE_SNIPPET}}
  ```
- **Target Code**:
  ```language
  {{AFTER_SNIPPET}}
  ```
- **Files Affected**: `{{FILE_1}}`, `{{FILE_2}}` (and callers listed in dependency map)
- **Breaking Risk**: NONE / LOW / MEDIUM / HIGH — {{EXPLANATION}}
- **User Consent Required**: [NOT_REQUIRED] or [AGREED] / [PENDING_USER_DECISION]
- **Minimum Changes Verification**:
  - [ ] Is this change strictly necessary to reach the target state? ✅ Yes / ❌ No → remove from plan
  - [ ] Can it be achieved with fewer file changes? ✅ Verified / ❌ Alternative: {{ALTERNATIVE}}
  - [ ] Does any existing pattern achieve the same result? Referenced: `{{FILE_PATH}}`, symbol(s): `{{SYMBOLS}}`

### C-02: {{CHANGE_TITLE}}
> Repeat structure for each proposed change.

## Regression Risk Analysis

| Change | Affected Test(s) | Predicted Result | Reason | Action Required |
| ------ | ---------------- | ---------------- | ------ | --------------- |
| C-01 | `tests/test_{{X}}::test_yyy` | PASS / FAIL / UNKNOWN | {{REASON}} | {{ACTION}} |

> **Note**: If predicted result is FAIL, STOP and discuss with user before proceeding to planning. Do NOT auto-fix or bypass failing tests.

## Ambiguities & Open Questions

| # | Question | Impact if Unresolved | Recommended Approach |
|---|---------|---------------------|---------------------|
| Q-1 | {{QUESTION_TEXT}} | Could lead to wrong implementation direction | Ask user: {{SPECIFIC_QUESTION}} |
| Q-2 | ... | ... | ... |

> **All open questions must be resolved by the user before transitioning from ANALYZED → PLANNED.**

## Caution Flags

Items that require manual review because automated analysis cannot determine correctness:

| Item | File / Symbol | Reason for Caution | Recommendation |
| ---- | ------------- | ------------------ | -------------- |
| C-FLAG-1 | `{{FILE}}` | {{REASON — e.g., "intentional complexity", "depends on runtime state"}} | Manual review recommended |

## Analysis Summary

| Metric | Value |
| ------ | ----- |
| Total problems identified | N |
| Proposed changes (C-N) | N |
| Files to be modified | N (`{{PATH_1}}, ...`) |
| Breaking risks requiring consent | N ([AGREED] / [PENDING]) |
| Tests at risk of regression | N |
| Open questions unresolved | N |
| Caution flags | N |
