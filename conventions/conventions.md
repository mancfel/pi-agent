# Global Conventions Index

This is the central entry point for all globally available coding conventions. Agents should read this file first to identify which topic modules apply to their current task.

## How to Use

1. **Identify your task context** — What language, framework, pattern, or testing approach will you be working with?
2. **Find matching topics below** — Each topic module covers a specific area of development.
3. **Read each relevant topic** — If the project has its own `conventions/<topic>.md`, use that instead (it overrides global). Otherwise, the global version applies.
4. **Apply all loaded conventions** consistently during implementation.

---

## Available Topic Modules

| Topic File | Description | When to Read |
|------------|-------------|--------------|
| [builder-pattern.md](./builder-pattern.md) | Fluent builder pattern conventions: class structure, scalar/primitive/complex setters, params arrays, Func delegates, sub-builder creation chain, anti-patterns | Implementing or reviewing fluent builder classes (C#) |
| [dotnet.md](./dotnet.md) | .NET / C# specific conventions: architecture layers, dependency injection, middleware, controllers, EF Core usage | Writing or reviewing C#/.NET code |
| [general.md](./general.md) | General coding principles: naming, comments, file structure, error handling patterns, code organization | Always read first as baseline; apply to all tasks |
| [nextjs-app-router.md](./nextjs-app-router.md) | Next.js App Router: Server Components by default, RSC Flight Protocol data fetching (never JSON parse), push client-to-leaves, route handlers with Zod validation | Building Next.js applications with the App Router |
| react.md | React / TypeScript frontend conventions: component patterns, hooks, state management, Tailwind CSS, no-nested-functions rule, Result pattern for errors | Building React components or TSX files |
| unit-test-dotnet.md | Unit testing in .NET: xUnit, FluentAssertions, NSubstitute, Arrange-Act-Assert, test naming, mocking strategies | Writing or reviewing unit tests for .NET projects |
| unit-test-react.md | Unit testing in React/TypeScript: Vitest/Jest, Testing Library, mock strategies, test coverage expectations | Writing or reviewing unit tests for React projects |

---

## Adding New Topic Modules

To add a new convention topic at the global level:

1. Create `~/.pi/agent/conventions/<topic-name>.md` with your conventions.
2. Add an entry to this index table above (in alphabetical order by file name).
3. Include a brief description and guidance on when agents should read it.

For project-level overrides, create `<project-root>/conventions/<topic-name>.md` — it will automatically take precedence over the global version during agent resolution.
