# Unit Testing Conventions (.NET)

These conventions apply when writing or reviewing unit tests in .NET projects using xUnit, FluentAssertions, and NSubstitute/Moq. They extend `general.md`.

## Test Framework & Libraries

- **xUnit** as the primary test framework (not NUnit or MSTest).
- **FluentAssertions** for expressive assertions — never use `Assert.Equal()` from xUnit directly.
- **NSubstitute** as the preferred mocking library; Moq is acceptable if already established in a project.
- **Verify** for middleware testing (ASP.NET Core).

## Naming Convention

Test method names follow a strict pattern that reads like a specification:

```
[MethodName]_Should_[Expected](_When_[Case])
```

The `_When_[Case]` suffix is **optional** and should be included only when the test verifies behavior under a specific condition or scenario. Omit it when the expectation is unconditional or obvious from the method name alone.

| Pattern | Example | When to Use |
|---------|---------|-------------|
| `[Method]_Should_[Result]` | `CalculateTotal_ShouldReturnZero_WhenCartIsEmpty` | Conditional / scenario-based tests (recommended) |
| `[Method]_Should_[Result]` | `ParseDate_ShouldThrowFormatException_OnInvalidInput` | Always include — describes precondition + outcome clearly |
| `[Method]_Should_[Result]` | `GetDisplayName_ShouldReturnFullName` | Simple, unconditional expectations |

### Test Class Naming

```csharp
// Class: <ClassBeingTested>Tests  (no "Unit" prefix)
public class UserServiceTests { }
public class OrderCalculatorTests { }
```

## Arrange-Act-Assert Pattern

Every test **MUST** follow the AAA pattern with explicit section markers. The comments `// Arrange`, `// Act`, and `// Assert` serve as visual anchors that clearly separate each phase of the test. These are mandatory — never omit them or merge sections together.

```csharp
/// <summary>
/// Tests when order is cancelled
/// Expected: When an order is cancelled then inventory should be restored for all line items
/// </summary>
[Test]
public void CancelOrder_ShouldRestoreInventory_WhenOrderIsPending()
{
    // Arrange
    var mockRepository = Substitute.For<IOrderRepository>();
    mockRepository.GetByIdAsync(orderId).Returns(mockOrder);
    _service = new OrderService(mockRepository, mockInventoryService);

    // Act
    var result = await _service.CancelOrderAsync(orderId);

    // Assert
    result.IsSuccess.Should().BeTrue();
    await mockInventoryService.Received(1).RestoreStockAsync(orderId);
}
```

### Section Rules

- **`// Arrange`** — Setup fixtures, create mocks with `Substitute.For<>()`, seed input data, configure dependencies. Nothing that executes the SUT goes here.
- **`// Act`** — Exactly one line: the call to the method under test. If multiple actions are needed, refactor into separate tests.
- **`// Assert`** — All verification assertions. Group related assertions together; do not interleave them with act or arrange code.

## Test Documentation (XML Summary Comments)

Every test method **MUST** include an XML `<summary>` comment describing what is being tested and the expected outcome in a Gherkin-style format. This makes test intent self-documenting for reviewers and future maintainers.

```csharp
/// <summary>
/// Tests that [brief description of scenario]
/// Expected: When [SomeCase / precondition] then [ActualValue] should be [ExpectedValue]
/// </summary>
[Test]
public void MethodName_Should_ExpectedResult() { }
```

### Examples

```csharp
/// <summary>
/// Tests when user does not exist
/// Expected: When GetUserByIdAsync is called with a non-existent ID then it should throw NotFoundException
/// </summary>
[Test]
public void GetUserById_ShouldThrowNotFoundException_WhenUserDoesNotExist() { ... }

/// <summary>
/// Tests that discount percentage is applied correctly
/// Expected: When a valid coupon code is provided then the final price should reflect the 15% discount
/// </summary>
[Test]
public void CalculateFinalPrice_ShouldApplyDiscount_WhenValidCouponIsProvided() { ... }

/// <summary>
/// Tests validation of empty email field
/// Expected: When an email string is null or whitespace then ValidateEmailAsync should return false
/// </summary>
[Test]
public void ValidateEmail_ShouldReturnFalse_WhenEmailIsNullOrWhitespace() { ... }
```

## Mocking Strategy

- **Mock only external dependencies** (databases, HTTP clients, message buses) — never mock the class being tested.
- **Minimize mock expectations** — Only assert on behavior that directly relates to the test's purpose.
- **Use `Substitute.ForPartial()` sparingly** — Prefer full mocks or real instances of collaborators where feasible.
- **Avoid over-mocking domain logic** — If you find yourself mocking 5+ dependencies for one test, consider if the SUT is too complex.

## Test Organization

- **One test project per main assembly** — Keep tests in a separate `{Assembly}.Tests` project.
- **Mirror namespace structure** — Tests should live in the same logical namespace as the code under test (e.g., `MyApp.Users.Tests`).
- **Test fixures** that are shared across multiple tests go in private helper methods or dedicated fixture classes — never in `[SetUp]`.

## Async Testing

- **Use async/await consistently** — No `.Result` or `.Wait()` in tests.
- **Set timeout on slow tests** (> 1 second) using `[Timeout(5000)]`.
- **Avoid race conditions** — Ensure mock setups and assertions happen synchronously after await returns.

## Coverage Expectations

- **Target ≥ 80% line coverage** for business logic; lower thresholds acceptable for thin adapters (controllers, mappers).
- **Test edge cases**: null inputs, empty collections, boundary values, invalid states.
- **Test failure paths** as thoroughly as success paths — every `catch` block should have a corresponding test.
