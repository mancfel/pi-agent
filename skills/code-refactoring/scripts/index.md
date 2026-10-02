# Code Refactoring Scripts Index

## Available Scripts

### `refactor_analyze.py`
**Path**: `scripts/refactor_analyze.py`  
**Purpose**: Builds dependency maps, identifies symbol usages across source files, and estimates breaking-change risk for refactoring planning. Supports Python (.py), C# (.cs), TypeScript/JavaScript (.ts/.js), and Java (.java).

**Usage**:
```bash
python refactor_analyze.py --target-dir <repo_root> [--symbol NAME] [--language py|cs|ts|java] [--output report.json] [--verbose]
```

**Parameters**:
| Flag | Required | Description |
|------|----------|-------------|
| `--target-dir` | Yes | Root directory of the target repository |
| `--symbol` | No | Filter analysis to a specific symbol name (exact match or prefix) |
| `--language` | No | Language code; auto-detected from file extensions if omitted |
| `--output` | No | JSON report output path (defaults to stdout) |
| `-v, --verbose` | No | Print progress details during scanning |

**Output**: JSON report containing:
- `dependency_map`: Per-symbol reference count, caller files, test impact
- `breaking_risk`: none/low/medium/high per symbol
- `estimated_change_count`: Number of files affected by changing each symbol

**Example**:
```bash
# Full analysis of a C# solution
python refactor_analyze.py --target-dir "D:/projectRoot" --language cs

# Analyze a specific class across all languages
python refactor_analyze.py --target-dir "D:/projectRoot" --symbol "UserService" --output deps.json
```
