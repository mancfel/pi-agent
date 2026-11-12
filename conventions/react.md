# React / TypeScript Frontend Conventions

These conventions apply specifically when building or reviewing React components, hooks, state management, and related frontend code. They extend `general.md`.

For **Next.js App Router** specific patterns (Server Components, RSC Flight Protocol, data fetching), see [nextjs-app-router.md](./nextjs-app-router.md).

## Component Structure

- **Functional components only** — No class components unless maintaining legacy code.
- **One component per file** with a named export (no default exports for components).
- **File naming**: PascalCase for component files (`UserProfile.tsx`), kebab-case for utility files (`format-date.ts`).
- **Co-locate related assets** — Keep styles, tests, and sub-components near the main component in feature folders:
  ```
  UserProfile/
    UserProfile.tsx
    UserProfile.test.tsx
    UserProfile.styles.ts
    useUserProfile.ts      (custom hook if logic extracted)
  ```

## Props & TypeScript

- **Define explicit prop interfaces** using `interface` keyword; name them `<ComponentName>Props`.
- **Prefer props interface over type alias** for components to allow merging via declaration merging if needed.
- **Destructure props** in function parameters with defaults instead of destructuring defaults at top level when defaults are simple.
- **Avoid `any`** — Use proper types or generics; prefer `unknown` over `any` when the shape is truly uncertain.

## Hooks

- **Custom hooks** must start with `use` and follow all Rules of Hooks.
- **Extract complex logic** into custom hooks when a component's render method exceeds ~30 lines of JSX.
- **Group related state** — If multiple pieces of state change together, keep them as one `useState` call.
- **Memoize expensive computations** with `useMemo`; memoize callback stability with `useCallback`.

## State Management

- **Local state first** — Start with React state (`useState`, `useReducer`) before reaching for global solutions.
- **Context API** for low-frequency updates (theme, auth); avoid for high-frequency data (lists, search results).
- **Server state** should use a dedicated library (TanStack Query / SWR) rather than local state; keep server and client state separate.
- **Zustand or Jotai** for complex client-side state that exceeds Context + reducer capabilities.

## Styling

- **CSS Modules or styled-components/Tailwind** — Pick one approach per project; do not mix.
- **Component-level styles** co-located with components, not in global CSS files.
- **No inline styles** except for dynamic values computed at runtime.

## Naming & Function Scope

- **Verb-first function names in camelCase**: `calculatePortfolioSummary`, `formatCurrency`, `resolveFxRate`.
- **Descriptive variable names** — avoid ambiguous abbreviations or single-letter names (except conventional loop counters `i`, `j`).
- **Booleans prefixed with indicative verbs**: `isActive`, `hasPermission`, `canSubmit`, `shouldRefresh`.

### No Nested Functions Rule

**Named functions MUST NOT be declared inside other functions or React components.** Extract all helpers to module level or utility files (`lib/`, `utils/`).

| Why | Detail |
|-----|--------|
| Hidden scope & coupling | Inner functions create implicit closures over outer variables, making it unclear what is captured. |
| Untestable code | Nested functions cannot be exported or unit-tested in isolation. |
| Performance degradation | In React components, nested function declarations are re-created on every render, pressuring the garbage collector and causing unnecessary child re-renders. |
| Cognitive overhead | Readers must scan through levels of nested closures to follow execution flow. |

**Acceptable exceptions**: short inline arrow callbacks passed directly into collection methods (`items.map((x) => x.id)`), or lightweight event handlers that simply delegate to an extracted handler.

## TypeScript & Type Safety

- **`strict: true` enabled at all times.** Never use `any` — use `unknown` for unvalidated external input and narrow via type guards or Zod schemas.
- **Never suppress errors with `@ts-ignore` or `@ts-nocheck`.** Solve the underlying incompatibility.
- **Explicit return types on exported functions** — serve as contracts and prevent accidental breaking changes during refactors. Do not rely on implicit return inference for complex domain calculations.
- **Zod for runtime validation** — derive TypeScript types directly from schemas:
  ```typescript
  import { z } from "zod";
  export const TransactionSchema = z.object({ id: z.string().uuid(), amount: z.number() });
  export type Transaction = z.infer<typeof TransactionSchema>;
  ```
- All data from external sources (APIs, user inputs, query params) must be validated at runtime with Zod before use.

## State Management & Data Flow

- **Compute derived values** — never store in `useState` what can be computed during render from props or existing state. Use `useMemo` for expensive derivations.
- **Custom hooks under `hooks/`** — encapsulate non-trivial logic, state transitions, and effects in named custom hooks (`usePortfolioFilter.ts`, `useTaxCalculation.ts`). Follow single responsibility per hook.

## Error Handling

- **Guard clauses & early returns** — handle edge cases, missing data, and invalid conditions first; return early to keep the happy path flat (max 2–3 nesting levels).
- **Return typed `Result` objects** instead of throwing exceptions for business logic and validation:
  ```typescript
  type Result<T> = { ok: true; data: T } | { ok: false; error: string };
  ```
- Reserve throwing exceptions only for unexpected fatal infrastructure errors (network timeout, DB connection loss).

## Styling (Tailwind CSS)

- Use Tailwind CSS utility classes directly on elements.
- When conditionally applying class names, use a `cn()` helper (`clsx` + `tailwind-merge`) — never inline ternary expressions in className strings.
- Avoid raw inline `style={{ ... }}` except for strictly dynamic computed values (e.g., chart coordinates).

## Routing

- **Use React Router v6+** nested route configuration for page-level routing.
- **Route guards / protected routes** via a wrapper component that checks auth state before rendering child routes.
- **Lazy-load route components** using `React.lazy()` and `Suspense` for code splitting.
