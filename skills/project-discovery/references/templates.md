# Discovery Report Template

Use this template when producing a project discovery report from the `project-discovery` skill. Save reports as `.agent/discovery-report-YYYYMMDD-HHmmss.md` in the target repository root.

## Template

```markdown
---
name: project-discovery
description: Discovers repository structure, stack, modules, interfaces, dependencies, tests, conventions and analogous implementations; produces an inventory report.
---

# Project Discovery Report — {{REPOSITORY_NAME}}

## Date
{{DATE}}

## Scope
- Target directory scanned: `{{TARGET_DIR}}`
- Total files analyzed: {{FILE_COUNT}}
- Languages detected: {{LANGUAGES}}

## Directory Structure (top-level)
```
{{STRUCTURE_TREE}}
```

## Entry Points
| Module / Entry | File Path | Language | Description |
| -------------- | --------- | -------- | ----------- |
| {{NAME}} | `{{PATH}}` | {{LANG}} | {{DESCRIPTION}} |

## Dependencies
### Runtime Dependencies
| Package | Version | Purpose |
| ------- | ------- | ------- |
| {{PKG}} | {{VER}} | {{PURPOSE}} |

### Development Dependencies
| Package | Version | Purpose |
| ------- | ------- | ------- |
| {{PKG}} | {{VER}} | {{PURPOSE}} |

## Test Structure
| Test Framework | Location | Files Found |
| -------------- | -------- | ----------- |
| {{FRAMEWORK}} | `{{PATH}}` | {{COUNT}} |

## Existing Conventions Detected
- **Naming**: {{NAMING_CONVENTIONS}}
- **Error Handling**: {{ERROR_HANDLING}}
- **Code Style**: {{CODE_STYLE}}
- **Documentation**: {{DOC_STYLE}}

## Analogous Implementations (if any)
| Feature / Pattern | File Path | Key Symbols | Reuse Signal |
| ----------------- | --------- | ----------- | ------------ |
| {{FEATURE}} | `{{FILE}}` | `{{SYMBOLS}}` | {{HIGH/MEDIUM/LOW}} |

## Notes & Caveats
- {{NOTES}}
```
