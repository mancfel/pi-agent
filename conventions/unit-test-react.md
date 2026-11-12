# Unit Testing Conventions (React / TypeScript)

These conventions apply when writing or reviewing unit tests for React components and hooks in TypeScript projects. They extend `general.md`.

## Test Framework & Libraries

- **Vitest** as the primary test runner (preferred over Jest for new projects); Jest is acceptable if already established.
- **Testing Library** (`@testing-library/react`, `@testing-library/jest-dom`) — test behavior from user perspective, not implementation details.
- **MSW (Mock Service Worker)** for API mocking at the network layer instead of manual `fetch` overrides.
- **TanStack Query testing utilities** for testing data-fetching components.

## Naming Convention

Test names follow a structured pattern that reads like a specification:

```
describe('[Component/Feature]')  → describes what is being tested
it('Should [Expected]_When_[Case]')  → describes the scenario and expected outcome
```

### describe Block Naming

Group tests under descriptive blocks named after the component or feature:

```typescript
// ✅ Good — clear subject + scope
describe('UserProfile', () => { ... });
describe('OrderCalculator', () => { ... });
describe('usePortfolioFilter hook', () => { ... });

// ❌ Bad — too vague
describe('utils', () => { ... });
describe('component', () => { ... });
```

### it() / test() Block Naming

Individual test names follow this pattern (adapted from the .NET convention for JavaScript/TypeScript):

```
it('[Action]_Should_[Expected](_When_[Case])')
```

The `_When_[Case]` suffix is **optional** and should be included only when the test verifies behavior under a specific condition or scenario. Omit it when the expectation is unconditional or obvious from the context.

| Pattern | Example | When to Use |
|---------|---------|-------------|
| `should[Result]_when[Scenario]` | `shouldThrowError_whenInputIsInvalid` | Scenario-based tests (recommended) |
| `should[Result]` | `shouldRenderLoadingSkeletonInitially` | Simple, unconditional expectations |
| `handles[action]_by[Result]` | `handlesClick_bySubmittingForm` | User interaction / event handler tests |

### Test File Naming

```typescript
// <ComponentName>.test.tsx for component tests
UserProfile.test.tsx

// <feature-or-utility>.spec.ts for hooks and utilities
usePortfolioFilter.spec.ts
formatCurrency.spec.ts
```

## Arrange-Act-Assert Pattern

Every test **MUST** follow the AAA pattern with explicit section comments. The lines `// Arrange`, `// Act`, and `// Assert` serve as visual anchors that clearly separate each phase of the test. These are mandatory — never omit them or merge sections together.

```tsx
it('shouldSubmitForm_withValidationErrors_WhenFieldsAreEmpty', async () => {
  // Arrange
  render(<UserProfileForm />);
  const submitButton = screen.getByRole('button', { name: /save/i });

  // Act
  await userEvent.click(submitButton);

  // Assert
  expect(screen.getByText('Name is required')).toBeInTheDocument();
  expect(screen.getByText('Email is required')).toBeInTheDocument();
});
```

### Section Rules

- **`// Arrange`** — Render the component, query DOM elements, mock dependencies via MSW handlers or vi.mock(), set up initial state. Nothing that triggers behavior goes here.
- **`// Act`** — Exactly one action: a user event (`click`, `type`), a hook update (`result.current.refresh()`), or an effect trigger. If multiple actions are needed, split into separate tests.
- **`// Assert`** — All verification assertions using Testing Library queries and matchers. Group related assertions together; do not interleave them with act or arrange code.

## Test Documentation (JSDoc Comments)

Every test block **SHOULD** include a JSDoc comment above it describing what is being tested and the expected outcome in a Gherkin-style format. This makes test intent self-documenting for reviewers and future maintainers.

```typescript
/**
 * Tests that [brief description of scenario]
 * Expected: When [SomeCase / precondition] then [ActualValue] should be [ExpectedValue]
 */
it('should[Result]_when[Scenario]', () => { ... });
```

### Examples

```tsx
describe('UserProfile', () => {
  /**
   * Tests when user data fails to load
   * Expected: When fetchUserByIdAsync throws an error then the component should display the error boundary with retry button
   */
  it('shouldShowErrorBoundary_whenApiReturnsFailure', async () => {
    // Arrange
    vi.mocked(useFetchUser).mockReturnValue({ loading: false, error: new Error('Network failure') });
    render(<UserProfile userId="123" />);

    // Act & Assert
    expect(screen.getByText('Failed to load profile')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  /**
   * Tests that avatar is displayed correctly
   * Expected: When a user has an avatar URL then the img element should show the avatar and alt text matches display name
   */
  it('shouldDisplayAvatar_whenUserHasProfileImage', async () => {
    // Arrange ...
  });
});

describe('usePortfolioFilter hook', () => {
  /**
   * Tests filtering by date range
   * Expected: When transactions are filtered between two dates then only matching transactions should be returned in the result array
   */
  it('shouldReturnFilteredTransactions_whenDateRangeIsSpecified', () => { ... });
});
```

## Testing Principles (Testing Library)

- **Test what the user sees and does** — Use queries like `screen.getByRole`, `screen.getByText`, `screen.getByLabelText`. Avoid querying by CSS class names or internal implementation details.
- **Never use `.internal` or private DOM selectors** in queries.
- **Prefer `toBeInTheDocument()`**, `toBeVisible()`, `toHaveTextContent()` over snapshot assertions for individual checks.
- **Use snapshots sparingly** — Only for complex, stable UI structures; never as the sole assertion.

## Component Testing

- **Render inside each `it()` block** — Never share a rendered instance across tests.
- **Use `act()` implicitly** via Testing Library's async helpers (`findBy*`, `waitFor`).
- **Mock external dependencies**: Context providers, API calls (via MSW), and third-party libraries.

## Custom Hook Testing

- **Use `@testing-library/react-hooks` or custom renderHook utility** for testing hooks in isolation.
- **Test all return values and edge cases**: initial state, updated state, error conditions.

```tsx
/**
 * Tests that loading state is true on first render
 * Expected: When the hook is called then isLoading should be true until data arrives
 */
it('shouldReturnLoadingTrue_onFirstRender', () => {
  const { result } = renderHook(() => useUserProfile(userId));
  expect(result.current.isLoading).toBe(true);
});
```

## Mocking Strategy

- **API calls → MSW handlers**, not `jest.spyOn(fetch)`.
- **Context providers → wrapper components** passed to `render()`, not global Provider overrides.
- **Third-party libraries → jest.mock() / vi.mock()` at the top of the test file.**
- **Timer-dependent code → advance timers explicitly**; never rely on real time in tests.

## Coverage Expectations

- **Target ≥ 80% branch coverage** for custom hooks and utility functions.
- **Test all render branches**: loading, error, empty state, success.
- **Test user interaction paths**: form validation, button clicks, keyboard navigation, accessibility concerns.
