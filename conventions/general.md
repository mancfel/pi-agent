# General Coding Conventions
These are universal coding principles applicable across all languages, frameworks, and projects unless explicitly overridden by a more specific convention file.

## Naming
- **Use meaningful, descriptive names** — Avoid abbreviations unless universally understood (e.g., `id`, `url`).
- **Follow language-native casing conventions**: PascalCase for types/classes/methods, camelCase for variables/functions, UPPER_SNAKE_CASE for constants.
- **Boolean variables/properties** should be prefixed with is, has, can, should, or similar predicates.
- **Avoid negative boolean names** — Prefer `isActive` over `isInactive`.
- **Test methods** follow the pattern: `TestMethod_WhenScenario_ThenExpectedOutcome`.

## File & Folder Structure
- **One public class per file** in languages that support it (C#, Java).
- **Co-locate related files** — Keep tests near source code (`UserValidator.cs` ↔ `UserValidatorTests.cs`).
- **Group by feature/domain**, not by type. A `Users` folder should contain controllers, services, models, and tests for users together.
- **Keep files reasonably short** — Aim for < 300 lines; extract when approaching this limit.

## Comments & Documentation
- **Comment "why," not "what"** — Code shows what it does; comments explain intent, edge cases, or trade-offs.
- **Use XML/doc-comments for public APIs** (C#) or JSDoc/TSDoc (TypeScript).
- **Avoid stale/outdated comments** — If a comment requires updating to stay accurate, update it with the change.
- **Always write comments in english**

## Error Handling
- **Never swallow exceptions** without logging or re-raising.
- **Prefer specific exception types** over generic catches.
- **Return domain-specific error objects/results**, not raw exceptions, at API boundaries.
- **Validate early** and return clear validation errors before processing begins.

## Code Organization
- **Single Responsibility Principle** — Each class/method should do one thing well.
- **Dependency Inversion** — Depend on abstractions, not concretions. Inject dependencies rather than creating them inline.
- **Keep functions small** — Aim for < 20 lines per method; extract logic into named helper methods.
- **Avoid god classes/modules** — If a file exceeds ~500 lines, consider splitting responsibilities.

## Git & Version Control
- **Write meaningful commit messages** — Format: `<type>(<scope>): <description>`. Use conventional commits (feat, fix, refactor, docs, test, chore).
- **Small, focused commits** — Each commit should represent one logical change.
- **Branch naming**: `feature/description`, `fix/description`, `refactor/description`.