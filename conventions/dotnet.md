# .NET / C# Conventions

These conventions apply specifically when writing or reviewing C# code in a .NET project. They extend and override where applicable from `general.md`.

## General Principles

- **Use the latest stable C# version** — Leverage modern language features (pattern matching, switch expressions, file-scoped namespaces, single-line usings).
- **Follow SOLID principles**, KISS, and DRY as foundational design guidelines.
- **Write clear comments explaining *why*** — especially for non-obvious design decisions; document library/external dependency usage and purpose.
- **All code and comments in English.**

## Formatting & Style

- **Apply `.editorconfig` formatting rules** — Do not deviate from project-defined formatting.
- **Prefer file-scoped namespace declarations** (`namespace MyNamespace;`) and single-line `using` directives where possible.
- **Insert a newline before the opening curly brace** of any code block (`if`, `for`, `while`, `foreach`, `using`, `try`, etc.).
- **Ensure final return statements are on their own line.**
- **Use pattern matching and switch expressions** wherever type checking/branching is needed instead of verbose if-else chains.
- **Use `nameof`** instead of string literals when referring to member names (e.g., in validation errors or event args).

## Architecture Layers

- **Follow layered architecture**: Controllers → Services → Repositories (if data access is abstracted) → Domain models.
- **Controllers should be thin** — Delegate business logic to service classes; controllers handle HTTP concerns only (routing, model binding, validation).
- **Use MediatR/CQRS pattern** for complex domains: separate commands (write) from queries (read), with dedicated handlers per operation.

## Dependency Injection

- **Inject dependencies via constructor injection** — Never use service locator or static factories.
- **Register services at startup** using the built-in DI container; prefer interface-based registration.
- **Lifetime management**: Use `Transient` for stateless services, `Scoped` for per-request state (e.g., EF Core DbContext), `Singleton` for truly global shared state.

## Controllers & API Design

- **RESTful resource naming** — Use plural nouns (`/api/users`, not `/api/getUser`).
- **Return appropriate HTTP status codes**: 201 for created, 204 for deleted/no-content, 400 for validation errors, 404 for not found.
- **Use ProblemDetails (RFC 7807)** for standardized error responses.
- **Apply `[ApiController]` attribute** to all controllers for automatic model state handling.

## Entity Framework Core

- **Use code-first migrations** — Define models in code; let EF generate and track database schema.
- **Avoid N+1 queries** — Use `.Include()`, `.ThenInclude()`, or projection (`Select`) judiciously.
- **Map entities explicitly** using Fluent API configuration rather than relying solely on conventions when the mapping is non-trivial.
- **Keep DbContext scoped** per request; never inject DbContext as singleton.

## Naming Conventions (C# Specific)

- **PascalCase** for class names, method names, and public members.
- **camelCase** for private fields and local variables.
- **_underscorePrefix** only for backing fields or constructor parameters that shadow properties.
- **Interfaces** prefixed with `I` (e.g., `IUserService`, `IRepository<T>`).
- **Async methods** suffixed with `Async` (e.g., `GetUserByIdAsync`).
- **XML doc comments required on all public APIs** — include `<summary>`, `<param>`, `<returns>`. When applicable, add `<example>` and `<code>` documentation blocks.

## Nullable Reference Types

- **Enable nullable reference types globally** — Set `<Nullable>enable</Nullable>` in the project file.
- **Declare variables non-nullable by default**; check for `null` only at entry points (API boundaries, factory methods).
- **Always use `is null` / `is not null`** instead of `== null` or `!= null` comparisons.
- **Trust the C# type system** — do not add redundant null checks when the compiler already guarantees non-nullability.
- **Use null-conditional operators** (`?.`) and null-coalescing (`??`) elsewhere where appropriate.

## Validation & Error Handling

- **Validate input at API boundaries** using FluentValidation (preferred) or DataAnnotations.
- **Implement a global exception handling middleware** that catches unhandled exceptions and returns consistent error responses.
- **Return RFC 9457 Problem Details** for standardized, machine-readable error responses. Use `<ProblemDetails>` with appropriate status codes and error types.
- **Handle edge cases explicitly** — log them, but never swallow exceptions silently.

## Logging & Monitoring

- **Use structured logging** with Serilog or equivalent provider — log contextual data as properties, not interpolated strings.
- **Log at appropriate levels**: `Information` for expected operations, `Warning` for recoverable issues, `Error` for failures requiring attention.
- **Implement correlation IDs** per request to enable end-to-end tracing across services and logs.
- **Integrate with Application Insights / OpenTelemetry** for telemetry collection, custom metrics, and distributed tracing.

## External Library Exploration (.NET Types Explorer MCP)

When writing code that depends on types from external libraries (NuGet packages, third-party assemblies) where source code is not available in the project:

1. **Always use the `.NET Types Explorer` MCP server** (`dotnet-types-explorer`) to discover the API surface of external assemblies before writing integration code.
2. **Exploration workflow**: Start with `ReferencedAssembliesExplorer(ProjectFileAbsolutePath)` → filter relevant NuGet assemblies → use `NamespacesExplorer(assemblyNames)` → use `NamespaceTypes(namespaces)` for detailed type signatures (methods, properties, constructors).
3. **Use `NuGetCache` or `Auto` resolution mode** for faster exploration without full builds — the server resolves packages directly from the NuGet global packages cache.
4. **For NuGet package discovery**: use `NuGetPackageSearch(SearchQuery)` to find packages, then `NuGetPackageVersions(PackageId)` to check version history and dependencies before adding references.
5. **Always pass absolute project paths** (e.g., `/workspace/my-project/MyProject.csproj`) since the MCP runs inside a Docker container with an isolated filesystem.
6. **Document findings in code comments** when using non-obvious APIs discovered via reflection — include the source assembly name and relevant namespace.

---

## Rider IDE Integration (JetBrains Rider MCP Server)

When performing development tasks that require IDE-level operations, always prefer using the JetBrains Rider MCP server (`dotnet-types-explorer` companion) over raw file edits. These tools provide semantic understanding of the codebase and guarantee correctness across all references.

### Refactoring Operations

- **Rename symbols**: Use `rename_refactoring(filePath, symbolName, newName)` for any identifier change — it updates ALL usages across the solution including `nameof()`, XML docs, XAML bindings, and Razor views. Never manually rename symbols.
  - Always run with `preview: true` first on public APIs to see the blast radius before committing.
  - Pattern: `{ok, applied, affects:{files,callSites}}`

- **Change method signatures**: Use `change_api_signature(filePath, methodName, parameters)` for adding/removing/reordering parameters — handles entire override/implementation hierarchy automatically.
  - Always preview with `preview: true` before applying.
  - CAUTION: Removing a parameter does NOT rewrite references inside method bodies — reported as warnings.

- **Extract interfaces/classes/methods**:
  - `extract_interface(filePath, typeName, interfaceName, members)` → creates interface from selected members of a class (fields and static members cannot be extracted).
  - `extract_base_class(filePath, typeName, baseClassName, members)` → moves selected members to a new base class; the original type inherits from it.
  - `extract_method(filePath, startLine, endLine, methodName)` → extracts statements into a new method. Parameters/return value/static-ness are inferred automatically.

- **Safe delete**: Use `safe_delete(filePath, symbolName)` — deletes only if no remaining usages exist. Refuses with conflict list otherwise. Never use raw deletion for symbols used in the solution.

- **Move types between namespaces**: Use `move_type_to_namespace(filePath, typeName, targetNamespace)` — updates all references across the solution.

- **Reorganize namespaces** (Adjust Namespaces): Use `reorganize_namespaces(scope)` where scope is either a project name or folder path. Syncs namespace declarations with folder structure and fixes using directives across the entire scope.

### Build & Quality Gates

- **Build operations**: Use `build_solution_start(rebuild: false)` for incremental builds; poll `build_solution_state(sessionId)` to track progress and collect problems. Never assume files compile without building first.

- **Quality checks on edited files**: Always run `lint_files(files, min_severity: 'warning')` after making changes — reports errors, warnings, and code-style suggestions per file. For post-edit hooks, use `post_edit_quality_check(file, reformat: true, run_inspections: true)` which reformats with solution style AND runs Rider inspections in one call.

- **Get project/solution info**: Use `get_solution_projects()` to list all projects before targeting them; `get_project_problems(severity, subsystem)` for build/NuGet/Roslyn diagnostics; `get_file_problems(filePath, errorsOnly)` for single-file analysis.

### Debugging Workflow (xDebug)

When debugging .NET applications:
1. Start session: `xdebug_start_debugger_session(configurationName or filePath+line)`
2. Set breakpoints programmatically: `xdebug_set_breakpoint(filePath, line, condition?)` — supports conditional breakpoints and logpoints (`logExpression + suspendPolicy: 'NONE'`).
3. Control execution: `xdebug_control_session(action)` with actions like `STEP_INTO`, `STEP_OVER`, `RESUME`, `PAUSE`, `STOP`.
4. Inspect state: `xdebug_get_frame_values(depth=0)` for locals/parameters; `xdebug_evaluate_expression(expression)` for computed checks in current frame context.
5. For exception-heavy code: use `xdebug_ignore_exception(exceptionType)` to suppress known expected exceptions (e.g., `System.OperationCanceledException`).

### Search & Navigation

- **Semantic symbol search**: Use `search_symbol(q, include_external: true/false)` — searches project symbols and optionally SDK/library types. Returns match coordinates (line/column).
- **Text/regex search**: Use `search_text(q, paths?)` or `search_regex(q, paths?)` for pattern-based discovery with exact line/column coordinates.
- **Symbol info at position**: Use `get_symbol_info(filePath, line, column)` to get full declaration details including type, documentation, and implementation hierarchy.
- **Find tests for a method**: Use `findTests(className, classNamespace, filePath, methodName?, methodArguments?)` to locate existing unit tests before writing new ones.
