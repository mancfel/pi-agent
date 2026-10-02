---
name: cs-unit-test
description: Generates high-quality C# unit tests using xUnit, FluentAssertions, and NSubstitute following the Arrange-Act-Assert pattern; enforces test isolation, proper mocking strategies, descriptive naming (Test_WhenX_ThenY), data-driven tests with Theory/InlineData, async testing best practices, and comprehensive edge-case coverage; produces test classes that compile cleanly against the target project.

---

# C# Unit Test Skill (`cs-unit-test`)

Use this skill as the **orchestration entry point** for generating or extending unit tests in a C#/.NET codebase. It produces tests using **xUnit**, **FluentAssertions**, and **NSubstitute** — strictly following the **Arrange-Act-Assert (AAA)** pattern and all established unit-testing best practices. All work is executed directly by the agent in foreground.

## FAST Test Characteristics
Every good unit test should satisfy the **FAST** criteria, adapted from Roy Osherove's principles:

| Criterion | Description |
| --------- | ----------- |
| **F**ast | Tests run in milliseconds. A mature project may have thousands of tests; they must be quick to execute so developers run them frequently. |
| **A**utonomous / Self-checking | Tests automatically detect pass/fail without human interpretation. No manual verification steps. |
| **S**eparate / Isolated | Tests are standalone with zero dependencies on outside state (filesystem, database, network). Running a test before or after another produces identical results. |
| **T**imely | Tests shouldn't take disproportionately longer to write than the code being tested. If testing takes 5× the development time, consider whether the design needs refactoring for testability. |

Tests that fail any of these criteria should be flagged during review and corrected.

## Core Principles (Non-Negotiable)
These principles govern every phase and decision:

| Principle | Description | Enforcement |
| --- | --- | --- |
| Arrange-Act-Assert Structure | Every test MUST follow AAA: one `// Act` line, everything else in Arrange or Assert sections with clear comments. | Violation = reject the generated test; re-generate with correct structure. |
| Test Isolation | Each test must be fully independent — no shared state between tests, no order dependency. Use `[Fact]` not `[TestCase]` for single-scenario tests; use `[Theory]` only when data varies but logic is identical.

Two valid fixture patterns exist:
- **Per-test creation (maximum isolation)**: Create SUT and mocks inside each test method. Best for tests with different mock configurations.
- **Constructor-based fixtures (shared immutable dependencies)**: Acceptable when ALL tests share the same dependency setup AND all dependencies are either NSubstitute mocks (which don't leak state) or produce fresh objects per call. NOT acceptable when constructor sets return values that cycle (`Returns(value1, value2)` pattern — see CAUTION below).
| No static fields used as mutable state across tests; do not use `.Returns(x, y, ...)` in constructors to encode test-specific behavior. |
| FluentAssertions Over Assertions | Never use `Assert.Equal()` directly — always use `.Should().Be()`, `.Should().BeNull()`, etc. | Every assertion uses FluentAssertions syntax. |
| NSubstitute for Mocks | Never create hand-rolled mocks/stubs — use NSubstitute's `Substitute.For<T>()`. | All fakes are created with NSubstitute or explicit fake classes in the same project. |
| Descriptive Naming | Test method names SHOULD follow one of three conventions:
  - **`Test_When<Scenario>_<Then<ExpectedBehavior>>`** — reads like a natural sentence (e.g., `Test_WhenUserHasNoOrders_ThenReturnsEmptyList`).
  - **`<MethodName>_<Scenario>_Returns<ExpectedBehavior>`** — MS docs convention, starts with the tested method name for easy scanning in test runners (e.g., `Add_EmptyString_ReturnsZero`).
  - **`<MethodName>_ShouldReturnX_WhenCondition`** — very common C#/.NET community pattern (e.g., `MapAsync_Should_Return_TypedMurexJsonInput`, `GetUserProfileById_ShouldThrowException_WhenNotFound`). This is arguably the most widely used naming style in enterprise C# projects.

Pick ONE and apply it consistently across ALL tests. Do NOT mix conventions within a project or even between related test classes.
| Private Member Encapsulation | Tests should NOT break encapsulation to test private methods. If you can't test something without making it internal/private, the design needs refactoring. | Skip "private method tests"; instead, test through public API surface. Use `[InternalsVisibleTo]` only if explicitly agreed by user. |
| No Magic Numbers or Strings | All magic values in tests must be extracted to named constants or use meaningful inline comments. | Every literal > 2 characters that isn't obviously a fixture value gets a descriptive name. |
| Read-Before-Write | Before editing any file, read its full current content first. Never work from stale snapshots. | Every `edit` operation must be preceded by a fresh `read` of the target file within the same turn or immediately before. AGENTS.md rule enforced strictly. |

## Execution Model — Single Agent, Foreground Only

> **All work is executed directly by the agent in foreground.** Do NOT spawn background sub-agents or parallel workers.
>
> - Run analysis commands yourself and parse results immediately.
> - Read cited files fully before referencing them.
> - Write test classes following this skill's patterns.
> - Apply edits one at a time, reading each file before editing.

## Admitted Input States
- `NEW` — fresh unit testing request from user (no tests exist yet)
- `EXISTING` — extending or modifying existing test classes/tests
- Any state where user has explicitly requested re-evaluation of an existing test scope

If no spec/test plan exists yet, create one with the appropriate context. If one exists, verify that the incoming state transition is permitted:

```plaintext
NEW → INVESTIGATING → ANALYZED → PLANNED → APPROVED → IMPLEMENTING → VERIFY → DONE
EXISTING → INVESTIGATING → ANALYZED → PLANNED → APPROVED → IMPLEMENTING → VERIFY → DONE
PLANNED → PLANNED         (revision loop — user requests plan changes)
APPROVED → PLANNED        (user rejects approval and asks for revisions first)
IMPLEMENTING → PLANNED    (reopening on conflict or compilation error)
VERIFY → PLANNED          (test failures found; revert to re-plan)
```

On invalid transition: emit `STOP` with explanation and halt.

## Feature Name Resolution

Before starting any phase, resolve the test scope name:

1. If the user provided a clear, unique class/method name in their request, use it.
2. If no name was given, or the requested name is ambiguous (e.g., "write tests", "add coverage"), **ask the user** which class(es) or method(s) need testing.
3. Store the resolved target as `<target-class-name>` and derive all paths from it:
   - Test file path convention: `src/<TestProject>/UnitTests/<TargetClass>UnitTests.cs`
   - Or existing test file if one already exists for this class.
4. Confirm the resolved name with the user before proceeding if it was inferred rather than explicitly stated.

### Examples of Good Names
- `UserService` → `UserServiceUnitTests.cs`
- `OrderValidator` → `OrderValidatorUnitTests.cs`
- `PaymentProcessor.ProcessAsync` → tests in `PaymentProcessorUnitTests.cs`

### Bad / Ambiguous Names (prompt user)
- "write some tests" → ask: "Which specific class or service should be tested?"
- "add unit tests to the project" → ask: "Which classes need test coverage first?"

## Prerequisites Check

Before starting, verify the target repository has these packages referenced in the test project's `.csproj`:

```bash
# Check for required NuGet packages in test project
rg 'xunit' <test-project-path>/*.csproj
rg 'FluentAssertions' <test-project-path>/*.csproj
rg 'NSubstitute' <test-project-path>/*.csproj
rg 'xunit.runner.visualstudio' <test-project-path>/*.csproj
```

If any package is missing, **STOP** and inform the user. The skill cannot produce correct tests without these dependencies. If they are present but at different versions, note the versions used and adapt accordingly.

Default expected packages:
| Package | Purpose | Minimum Version |
| ------- | ------- | --------------- |
| `xUnit` | Test framework | 2.4.0+ |
| `xunit.runner.visualstudio` | VS/CLI runner | 2.4.0+ |
| `FluentAssertions` | Assertion library | 6.0+ |
| `NSubstitute` | Mocking framework | 5.0+ |
| `Microsoft.NET.Test.Sdk` | Test SDK (implicit) | 17.0+ |

## Workflow Phases

The skill performs these phases sequentially. **Every phase must respect the AGENTS.md rules** — read files before writing, and always check for `CONVENTIONS.md` / `ARCHITECTURE.md` before planning or implementing.

---

### Phase 0: Context Loading & Scope Definition (Pre-Work)

> **This is mandatory. No work begins until this step completes.**

Before any other phase starts, the agent MUST:

1. **Check for existing project documentation** in the repository root:
   ```bash
         ls <repo-root>/CONVENTIONS.md      # if exists → READ FULL FILE
         ls <repo-root>/ARCHITECTURE.md     # if exists → READ FULL FILE
   ```
2. If either file exists, read it completely and store its content in context. Identify rules that apply to test files (e.g., naming conventions, folder structure).
3. If neither file exists, delegate to `project-discovery` skill which will create them during discovery. Do NOT proceed until conventions/architecture are known.
4. **Confirm target repository path** and **target class/method** with the user before proceeding.

---

### Phase 1: Investigation (`NEW/EXISTING → INVESTIGATING`)

The agent investigates the code under test to understand what needs testing.

#### Step 1.1: Locate Target Class(es)

```bash
# Find the class or interface to be tested
rg "class <TargetClass>" --type cs -l | head -20
rg "interface I<TargetClass>" --type cs -l | head -20
```

Read the full content of every source file for the target class(es). Identify:
- Public and internal methods (testable surface area)
- Constructor parameters (dependencies that need mocking)
- Interfaces used via dependency injection
- Exception-throwing paths
- Async methods (`Task`, `ValueTask`)
- Static methods (cannot be mocked directly — flag as CAUTION)

#### Step 1.2: Check for Existing Tests

```bash
# Look for existing test files
find <repo-root> -path "*Tests*" -name "*<TargetClass>*" -type f
find <repo-root> -path "*Test*" -name "*<TargetClass>*" -type f
rg "<TargetClass>" --glob *Test*.cs --type cs -l | head -20
```

If tests already exist, read them fully and identify gaps:
- Which public methods are NOT tested?
- What edge cases are missing?
- Are existing tests following AAA pattern correctly?

#### Step 1.3: Map Dependencies & Mocking Needs

For each constructor parameter or method dependency of the target class:

| Dependency Type | Treatment | Example |
| --------------- | --------- | ------- |
| Interface (`IRepository`) | NSubstitute mock: `Substitute.For<IRepository>()` | — |
| Concrete class with virtual members | NSubstitute proxy: `Substitute.For<MyClass>()` | — |
| Value type / struct / primitive | Inline fixture value in Arrange | `new DateTime(2024, 1, 1)` |
| String configuration | Inline string literal in Arrange | `"ConnectionString"` |
| Non-mockable third-party class (sealed, no interface) | Create adapter/fake or use `[InternalsVisibleTo]`; flag as CAUTION | — |

#### Step 1.4: Identify Test Scenarios

For each public/internal method on the target class, identify scenarios:

| Scenario Category | What to Cover |
| ----------------- | ------------- |
| Happy path | Normal input → expected output |
| Null inputs | Null parameters → appropriate exception |
| Empty collections | Empty list/enum → correct behavior |
| Boundary values | Min/max/zero/near-zero values |
| Invalid state | Object in unexpected state → exception or graceful handling |
| Async completion | Task completes successfully with correct result |
| Async exceptions | Task throws exception (not null Result) |
| Side effects | State changes are as expected (verify via assertions or `Received()` calls on mocks) |

#### Step 1.5: Set Status & Report

Set status to `INVESTIGATING` and produce an initial investigation summary. Ask the user: *"Does this scope cover everything you intended? Are there any additional methods or edge cases I should include?"* If not, refine before proceeding.

---

### Phase 2: Analysis (`INVESTIGATING → ANALYZED`)

This is the core analytical phase where the agent determines exactly which tests to write and how they will be structured.

#### Step 2.1: Test Plan Matrix

Create a traceability matrix mapping each method/scenario to its test plan:

| Method | Scenario | Test Name Pattern | Arrange Notes | Assert/Verify Notes |
| ------ | -------- | ----------------- | ------------- | -------------------- |
| `GetOrders()` | Happy path | `Test_WhenCustomerHasOrders_ThenReturnsOrders` | Mock repo returns list | `.Should().NotBeEmpty()`, count matches |
| `GetOrders()` | No orders | `Test_WhenCustomerHasNoOrders_ThenReturnsEmptyList` | Mock repo returns empty | `.Should().BeEmpty()` |
| `ProcessPayment(amount)` | Null amount | `Test_WhenAmountIsNull_ThenThrowsArgumentNullException` | — | `.Should().Throw<ArgumentNullException>()` |

#### Step 2.2: Test Class Structure Design

Determine the structure of each test class:

```csharp
// Each test class MUST follow this template:
public class <TargetClass>UnitTests       // NOT "<TargetClass>Tests" or "Test<TargetClass>"
{
    private readonly IMyDependency _mockDep;      // NSubstitute mocks as readonly fields
    private readonly MyService _sut;              // SUT = System Under Test, readonly field

    public <TargetClass>UnitTests()               // Constructor for shared setup
    {
        _mockDep = Substitute.For<IMyDependency>();
        _sut = new MyService(_mockDep);            // SUT created here
    }
}
```

Key decisions to document:
- Which dependencies are mocked vs. real?
- Will tests share a constructor-based fixture, or will each test create its own objects (preferred for maximum isolation)?
- Are any `[Collection]` attributes needed (for tests sharing state — rare and discouraged)?

#### Step 2.3: Regression Risk Analysis

For every planned test scenario:

1. Identify if existing tests might be affected by the new test file.
2. If extending an existing test class, verify no naming conflicts with existing methods.
3. Flag any scenarios that require modifying production code (e.g., making internal visible) as requiring user consent.

#### Step 2.4: Ambiguity & Conflict Resolution

If during analysis you encounter:

- Unclear expected behavior → ask the user specific questions
- Methods that depend on external systems (DB, HTTP, filesystem) → mark as CAUTION and recommend integration test approach instead of unit test
- Sealed classes without interfaces → flag for refactoring discussion; propose adapter pattern or mockable interface
- Complex business logic spanning multiple methods → suggest testing the orchestration method rather than each sub-method individually

**Never proceed past Phase 2 with unresolved ambiguities.** Report every open question to the user before transitioning to PLANNED.

#### Step 2.5: Set Status & Transition

Set status to `ANALYZED`. Produce the analysis report. Present findings to the user and confirm: *"Are all identified scenarios correct? Are there any additional concerns?"* Only after confirmation, transition to Phase 3.

---

### Phase 3: Planning (`ANALYZED → PLANNED`)

Create a detailed implementation plan that specifies exactly which tests will be written — but do NOT modify any source files yet.

#### Step 3.1: Generate Test Plan Artifact

Create a test plan at `specs/<target-class>/test-plan.md` (or append to existing spec):

```markdown
# Test Plan — <TargetClass>

## Date
YYYY-MM-DD

## Status
PLANNED

## Target Class
- Full path: `<repo-root>/<path-to-source-file>.cs`
- Namespace: `Company.Project.<Namespace>`
- Dependencies requiring mocks:
  - `IOrderRepository` → NSubstitute mock
  - `IPaymentGateway` → NSubstitute mock

## Test Scenarios Planned

| # | Method | Scenario | Test Name | Type | Priority |
|---|--------|----------|-----------|------|----------|
| 1 | GetOrders() | Customer has orders | `Test_WhenCustomerHasOrders_ThenReturnsOrders` | Fact | HIGH |
| 2 | GetOrders() | Customer has no orders | `Test_WhenCustomerHasNoOrders_ThenReturnsEmptyList` | Fact | HIGH |
| ... | ... | ... | ... | ... | ... |

## Mocking Strategy
- All interfaces mocked via `Substitute.For<T>()`.
- No hand-rolled fakes needed.

## Known Gaps / CAUTION Items
- Method X depends on DateTime.Now — will use a wrapper or time provider pattern.
```

#### Step 3.2: Zero-Code-Change Verification

Before setting status to PLANNED, verify:

1. No source files have been modified since the investigation phase.
2. Working tree is clean in the target repository.
3. The test plan covers all public/internal methods identified in Phase 1.

If any code has been accidentally modified → revert and notify user immediately.

#### Step 3.3: Set Status & Request Approval

Set status to `PLANNED`. Present the complete test plan to the user with a clear summary of:

- Total number of tests planned
- Mocking strategy summary
- Any CAUTION items requiring discussion
- Estimated file(s) to be created/modified

Ask explicitly: *"Do you approve this test plan? Shall I proceed with writing the tests?"* Only on explicit approval does the workflow advance.

---

### Phase 4: Implementation Gate (`PLANNED → APPROVED`)

**CRITICAL GATE** — If any source file has been modified since Phase 0, STOP immediately. This is a protocol violation that must be corrected before proceeding.

**Approval Checklist** — present each item and wait for user acknowledgment:

1. All test scenarios are understood and accepted.
2. The mocking strategy covers all dependencies appropriately.
3. Each test follows AAA structure (Arrange-Act-Assert).
4. Test names follow `Test_WhenX_ThenY` convention.
5. FluentAssertions syntax will be used throughout (no raw Assert calls).
6. Auto-generated files excluded: Verify that NO task references `.g.cs`, `Designer.cs`, or any file with `<auto-generated />` directive.
7. If extending existing tests, confirm no conflicts with existing methods.

On approval: set status to `APPROVED`.

---

### Phase 5: Implementation (`APPROVED → IMPLEMENTING`)

Execute the approved test plan by writing actual test code. This is where tests are created/extended.

#### Step 5.1: Pre-Task Verification

Before executing each batch of tests:

1. **Read CONVENTIONS.md** in repository root — if exists, read full content and verify alignment (test naming, folder structure).
2. **Read ARCHITECTURE.md** in repository root — if exists, read full content and verify no architectural boundary violations.
3. Read the target source file(s) fully to confirm exact method signatures, parameter types, and return types.

#### Step 5.2: Write Tests Following AAA Pattern Strictly

For EACH test, follow this exact structure template:

```csharp
using FluentAssertions;
using NSubstitute;
using Xunit;

namespace Company.Project.UnitTests;

public class TargetClassUnitTests
{
    private readonly IDependency _mockDependency = Substitute.For<IDependency>();
    // OR create per-test for maximum isolation (preferred):
    // No shared constructor state unless absolutely necessary.

    [Fact]
    public async Task Test_WhenUserHasValidId_ThenReturnsActiveUser()
    {
        // ─── ARRANGE ──────────────────────────────────────────────
        var expectedUser = new User(1, "john@example.com", "John");
        _mockDependency.GetUserAsync(1).Returns(expectedUser);

        var service = new TargetService(_mockDependency);

        // ─── ACT ──────────────────────────────────────────────────
        var result = await service.GetUserAsync(1);

        // ─── ASSERT ───────────────────────────────────────────────
        result.Should().NotBeNull();
        result.Email.Should().Be("john@example.com");
        result.Name.Should().Be("John");

        // Verify mock interactions (if applicable)
        await _mockDependency.Received(1).GetUserAsync(1);
    }
}
```

**AAA rules enforced:**
- Exactly ONE statement between `// Act` and `// Assert` comments — the method invocation under test.
- All setup, mocks configuration, and fixture creation go in Arrange section.
- ALL assertions and verifications go in Assert section.
- No interleaving: never Assert → Arrange again within a single test.
- Use `// ─── ARRANGE ───`, `// ─── ACT ───`, `// ─── ASSERT ───` comment separators for clarity (40 dashes).

#### Step 5.2a: Builder Pattern for Complex Arrange

When the SUT or its dependencies require constructing complex objects, use builders with fluent method chaining:

```csharp
// Arrange using builder pattern (recommended over manual object construction)
var bookingInfo = new MurexCommodityBookingInfoBuilder()
    .WithTestValues()
    .WithClientPricePerUnit(45M)
    .WithTradingPricePerUnit(tradingPrice)
    .WithProductsPriceData(builder => builder
        .WithClientPricePerUnit(22)
        .New()
        .WithClientPricePerUnit(65)
    )
    .Build();
```

**When to use builders:**
- Objects have 5+ properties that affect the tested behavior
- The same fixture data is needed across multiple tests (via base class factories)
- Nested object graphs are involved

**When NOT to use builders:**
- Simple objects with ≤3 relevant properties — inline construction is clearer
- Testing edge cases where you need minimal input (`0`, `""`, `null`) — builders obscure what's actually being tested

#### Step 5.2b: Generic Test Base Classes for Polymorphic Testing

When testing a family of related classes (e.g., different mapper implementations with the same interface), use abstract generic base classes:

```csharp
public abstract class SpreadMapperTestBase<TProduct, TFirstLeg, TSecondLeg> : MapperTestsBase
    where TProduct : Product
    where TFirstLeg : Product
    where TSecondLeg : Product
{
    protected readonly IMapper<TFirstLeg> FirstLegMapper;
    protected readonly IMapper<TSecondLeg> SecondLegMapper;
    
    // Abstract methods that concrete tests must implement
    protected abstract DateTime NearEffectiveDate(TFirstLeg leg);
    protected abstract void SetNearFixedPrice(TFirstLeg leg, decimal price);
}
```

This pattern is legitimate and recommended when:
- Testing multiple concrete implementations of a shared abstraction
- Each test subclass provides type-specific fixture setup via abstract method overrides
- The base class handles common mock configuration and assertion helpers

**Guardrail**: Never make the generic parameters optional (e.g., `where TProduct : Product = SomeDefault`). Always require explicit type specification in derived classes.

#### Step 5.3: FluentAssertions Syntax Rules

| Assertion Type | Correct Usage | Incorrect Usage |
| -------------- | ------------- | --------------- |
| Equality | `.Should().Be(expected)` | `Assert.Equal(expected, actual)` |
| Null check | `.Should().BeNull()` / `.Should().NotBeNull()` | `Assert.Null(actual)` |
| Exception | `.Should().Throw<ArgumentException>()` | `Assert.Throws<ArgumentException>` |
| Collection | `.Should().Contain(x => x.Id == 1)` | `collection.Any(c => c.Id == 1).Should().BeTrue()` |
| Async exception | `.Should().ThrowAsync<TException>()` | `.Should().Throw<TException>()` on Task |
| String | `.Should().StartWith("prefix")` | `"prefix" == str.Substring(0, 6)` |
| Property | `.Should().HaveProperty(nameof(User.Name))` | Manual property access checks |

#### Step 5.4: NSubstitute Usage Rules

**Stub vs Mock distinction:** When using NSubstitute, understand whether your fake object is being used as a stub or a mock:

```csharp
// STUB: Provides return values but NOT verified via Received()
var stubOrder = Substitute.For<IOrder>();
stubOrder.IsValid.Returns(true);
// No Received() calls — the test asserts on SUT behavior, not on interactions with stubOrder
```

| Concept | How NSubstitute represents it |
| ------- | ----------------------------- |
| **Stub** | `Substitute.For<T>()` + `.Returns(...)` only. NOT verified with `Received()`. Use when you need a dependency just to satisfy constructor requirements. |
| **Mock** | `Substitute.For<T>()` + `.Returns(...)` + `_mock.Received(1).Method()` interaction assertion. Use when verifying that specific calls were made. |
| **Fake** | Generic term: can be used as either a stub or mock depending on whether assertions are made against it (follows Roy Osherove's definitions from MS .NET best practices guide). |

This terminology follows Roy Osherove's definitions and the Microsoft .NET best practices guide.

// ✅ Correct — setup return value
_mockRepo.GetOrders(Arg.Is<int>(id => id > 0)).Returns(orderList);

// ✅ Correct — setup async return value  
_mockGateway.ProcessPaymentAsync(Arg.Any<PaymentRequest>())
    .Returns(Task.FromResult(new PaymentResult(true, "TX123")));

// ✅ Correct — verify received call (async)
await _mockGateway.Received(1).ProcessPaymentAsync(Arg.Any<PaymentRequest>());

// ❌ Wrong — mixing xUnit Assert with FluentAssertions in same test
Assert.NotNull(result);           // Don't do this
result.Should().NotBeNull();     // Do this instead

// ✅ Correct — throw exception from mock
_mockRepo.GetById(999).Throws(new KeyNotFoundException("User not found"));

// ✅ Correct — setup callback on call
_mockLogger.Received().LogError(Arg.Any<string>());

// ✅ Correct — partial substitute for class with virtual members
var partialMock = Substitute.ForPartsOf<MyService>(_realDependency);
partialMock.CalculateDiscount().Returns(10m);

#### Advanced: Inspecting Received Calls — For complex verification scenarios where `Received(1)` isn't sufficient, you can inspect all received calls:
```csharp
var receivedArgs = _mock.ReceivedCalls()
    .Where(c => c.GetMethodInfo().Name == "ProcessAsync")
    .Select(c => (MyArgType)c.GetArguments()[0])
    .ToArray();
receivedArgs.Should().HaveCount(2);
```
Use this sparingly — prefer explicit `Received(n).Method()` assertions. ReceivedCalls inspection is most useful in custom assertion helpers on test base classes for polymorphic testing.

// ❌ Wrong — trying to mock sealed classes directly (use interface or adapter)
// var sealedMock = Substitute.For<SealedClass>();  // Compile error!
```

#### Step 5.4a: Write Minimally Passing Tests (MS Best Practice)

When writing test inputs, use the simplest values that exercise the behavior being tested. Over-specifying input data makes tests brittle and harder to understand when they fail.

| Principle | Example | Anti-pattern |
| --------- | ------- | ------------ |
| Use `0` instead of `42` for sum-zero edge case | `.Add("0")` → expect `0` | `.Add("42")` → expect `42` (unnecessary complexity) |
| Use empty string instead of complex string | `.Add("")` → expect `""` | `.Add("hello world with spaces")` (confusing failure messages) |
| Use minimal object state | Only set properties that affect the tested behavior | Set all 15 properties on a DTO when testing one method |

**Why it matters:** When a minimally-passing test fails, you immediately know what changed. A test using many fixture values makes it harder to identify which input caused the failure.

#### Step 5.4b: Avoid Coding Logic in Unit Tests (MS Best Practice)

Never include manual loops (`foreach`, `for`, `while`), conditional branches (`if`, `switch`), or string manipulation inside unit tests. If your test contains branching logic, you risk introducing bugs into your test suite — the last place you want a bug is in code that validates other code.

**Wrong:** Manual loop with incrementing expected values
```csharp
[Fact]
public void Add_MultipleNumbers_ReturnsCorrectResults()
{
    var calculator = new StringCalculator();
    var expected = 0;
    var testCases = new[] { "0,0,0", "0,1,2", "1,2,3" };

    foreach (var test in testCases)
    {
        Assert.Equal(expected, calculator.Add(test));
        expected += 3;   // BUG: logic inside test — if this increments wrong, tests pass incorrectly
    }
}
```

**Correct:** Use `[Theory]` + `[InlineData]` to express each input/output pair explicitly
```csharp
[Theory]
[InlineData("0,0,0", 0)]
[InlineData("0,1,2", 3)]
[InlineData("1,2,3", 6)]
public void Add_MultipleNumbers_ReturnsSumOfNumbers(string input, int expected)
{
    var calculator = new StringCalculator();
    var actual = calculator.Add(input);
    actual.Should().Be(expected);
}
```

When you see a test with loops or conditionals: **STOP** and convert it to `[Theory]` + `[InlineData]` (or `ClassData` for complex objects). Each row in the theory data represents one distinct scenario that can be independently verified.

#### Step 5.5: Data-Driven Tests with Theory

When multiple input/output combinations test the same logic, use `[Theory]`:

```csharp
[Theory]
[InlineData("valid@email.com", true)]
[InlineData("invalid-email", false)]
[InlineData("", false)]
[InlineData(null, false)]
public void Test_WhenEmailIsValidOrNot_ThenValidationResultIsCorrect(string email, bool expectedValid)
{
    // Arrange
    var validator = new EmailValidator();

    // Act
    var result = validator.IsValid(email);

    // Assert
    result.Should().Be(expectedValid);
}
```

For complex objects as theory data, prefer `ClassData` or `MemberData`:

```csharp
public static IEnumerable<object[]> ProcessPaymentTestData => new object[]
{
    new object[] { 10.0m, "USD", true },   // Valid amount + valid currency
    new object[] { -5.0m, "USD", false },   // Negative amount
    new object[] { 0m, "EUR", false },      // Zero amount
};

[Theory]
[ClassData(typeof(ProcessPaymentTestData))]
public void Test_WhenPaymentAmountIsInvalid_ThenThrowsArgumentException(decimal amount, string currency, bool shouldSucceed)
{
    // Arrange
    var processor = CreateProcessor();

    // Act & Assert
    if (shouldSucceed)
        () => processor.Process(amount, currency).Should().NotThrow();
    else
        () => processor.Process(amount, currency).Should().Throw<ArgumentException>();
}
```

#### Step 5.6: Async Testing Best Practices

```csharp
// ✅ Correct — async test method returns Task
[Fact]
public async Task Test_WhenFetchingDataAsync_ThenReturnsResult()
{
    // Arrange ...
    var result = await _sut.GetDataAsync();
    // Assert ...
}

// ❌ Wrong — async void (will cause xUnit to miss exceptions)
[Fact]
public async void BadTestName() { }

// ✅ Correct — assert exception from async method
await FluentAssertions.AwaitExtensions
    .Invoking(async s => await s.FailingMethod())(_sut)
    .Should().ThrowExactly<InvalidOperationException>();

// Or simpler:
await FluentAssertions.ShouldMethodInvocationExtensions.Invoking(s => s.AsyncMethod()).Should()
    .ThrowAsync<TException>();
```

#### Step 5.7: Apply Edits and Compile Gate

For each test file or class being created/modified:

1. **Read target file** (full content) if it exists, or create new file with proper namespace and imports.
2. **Apply changes precisely**: Write only the tests specified in the approved plan. Do NOT add "nice-to-have" tests that were not approved. If you discover additional scenarios while working, STOP and ask the user whether to include them.
3. **FAIL-FAST COMPILATION GATE — Mandatory after every test batch**: Before moving on, run a full project build:
   ```bash
         dotnet build --no-restore <solution_or_test_project> -v q
   ```
   **Build result handling:**

| Result | Action |
| ------ | ------ |
| Build succeeds (exit code 0) | Proceed to next test or file. |
| Build fails with warnings only | Check if new or pre-existing. All pre-existing → proceed. Any new warning → document and revert task edits. |
| Build fails with errors | **FAIL-FAST TRIGGERED.** Stop immediately. Document error details. Fix the compilation issue in the test code, re-read affected files, retry build. Do NOT proceed until clean compile. |

4. **Run existing tests** for the affected project to ensure no regressions:
   ```bash
         dotnet test <test-project> --no-build -v n
   ```

#### Step 5.8: Auto-Generated File Protection During Implementation

**Absolute rule**: Never edit an auto-generated file. If a generated file happens to be referenced (e.g., `*.generated.cs`), STOP and redirect changes to the developer-authored partial class/interface instead. Log the substitution.

---

### Phase 6: Verification (`IMPLEMENTING → VERIFY`)

After all planned tests are written and compiling cleanly:

#### Step 6.1: Run Full Test Suite for Affected Project

```bash
dotnet test <test-project> -v normal --logger "console;verbosity=detailed"
```

Record pass/fail counts and any failures with their error messages.

#### Step 6.2: Verify Coverage Completeness

For each public/internal method on the target class, confirm at least one test exists that exercises it (happy path). Document gaps if any remain.

| Method | Happy Path Test | Edge Cases Covered | Status |
| ------ | -------------- | ------------------- | ------ |
| `GetOrders()` | ✅ `Test_WhenCustomerHasOrders...` | null input, empty result | ✅ Complete |
| `ProcessPayment()` | ✅ `Test_WhenAmountIsPositive...` | negative amount, zero amount | ⚠️ Missing: currency validation |

#### Step 6.3: Assess Results

| Result | Action |
| --- | --- |
| All tests pass + all planned scenarios covered | Set status to VERIFY → proceed to Phase 7 |
| Some tests fail (assertion or compilation) | REGRESSION DETECTED — set status back to PLANNED, document which tests failed and why, ask user for direction |
| Compilation errors unresolved | Stop immediately, document error details, revert to IMPLEMENTING with conflict log |

---

### Phase 7: Completion (`VERIFY → DONE`)

1. Present a final summary to the user:
   - What was created/modified (test file paths, number of new tests)
   - Test results (pass/fail counts)
   - Coverage gaps identified (methods not yet tested)
   - Any deviations from the approved plan

2. If there are deviations or remaining gaps, explain them clearly.

3. Set status to `DONE`.

4. **Propose** updates to project documentation (e.g., add test coverage metrics to ARCHITECTURE.md). Do NOT apply automatically — present for approval.

---

## Revision vs Implementation Signal

When the agent receives any request while in `PLANNED` or `ANALYZED` state:

| User says... | Intent Classification | Action |
| --- | --- | --- |
| "change X", "modify Y", "update Z" (referring to plan content) | **Revision** — stay in planning mode | Update relevant spec artifact(s), keep status as current state |
| "fix something discovered during review" | **Revision** — update plan first | Apply changes to specs, ask for re-review if needed |
| "implement these tests", "start writing tests", "go ahead" | **Implementation** — proceed to Phase 5 | Verify status is `APPROVED`, invoke implement logic |
| "apply the fix directly" (bypassing plan) | **Escalation** — confirm before bypassing | Ask user: "Do you want to update the plan first or skip straight to code?" |

If intent is unclear, **always default to revision mode**. Never assume a change request means "also write more tests."

---

## State Management

Each spec file uses YAML frontmatter with a `status:` field. The skill reads this at phase boundaries:

```yaml
---
status: PLANNED          # Current state
created_date: 2026-09-07
updated_date: 2026-09-07 # Updated on every change
tags: [test-plan, csharp]
target_class: UserService
---
```

### Update Pattern
When transitioning states, update only the `status` and `updated_date` fields:

```python
# Before transition
frontmatter["status"] = new_status
frontmatter["updated_date"] = today()
```

## Artifact Paths Reference

| Format | Path Pattern | Example |
| --- | --- | --- |
| Test plan (full) | `specs/<target-class>/test-plan.md` | `specs/user-service/test-plan.md` |
| New test file | `<repo-root>/<TestProject>/UnitTests/<TargetClass>UnitTests.cs` | `src/Company.Project.UnitTests/UserServiceUnitTests.cs` |
| Existing test file to extend | Same convention as above, found via search in Phase 1 | — |
| Compact test plan | `.pi/plans/<target-class>-tests.md` | `.pi/plans/user-service-tests.md` |

---

### Pre-Implementation Enforcement (Bypass Prevention)

The following behaviors indicate an agent bypassed required gates. These MUST be detected and corrected:

| Violation | Detection Method | Required Correction |
| --- | --- | --- |
| Test files modified before APPROVED state | `git diff --stat` shows changes when status ≠ APPROVED/IMPLEMENTING | Revert all unauthorized edits; trace which phase was skipped |
| Tests written without spec artifacts | No files under `specs/<target-class>/` exist | Create test plan first; present for approval |
| Raw Assert.* calls used in tests | Grep for `Assert\.` in generated test files | Replace with FluentAssertions `.Should()` syntax |
| Non-AAA structure detected | Read each test and verify Arrange → Act → Assert ordering | Refactor the test to correct structure |

If any violation is detected:

1. **STOP ALL WORK**.
2. Report the exact violation to the user with evidence (grep results, git diff).
3. Revert unauthorized code changes or refactor non-compliant tests.
4. Resume from the correct phase only after user acknowledgment.

### Implementation Gate STOP Rule

Before ANY implementation begins:

```plaintext
STOP: Implementation requires status APPROVED. Current status: {current_status}.
No changes will be made until user confirms approval.
```

Additionally, before **every single file edit** during Phase 5 (Implementation):

```plaintext
STOP: Read-before-write rule — have I read the full current content of the target file?
If NO → READ NOW. Do NOT proceed with edits.
```

---

## Repository Root Resolution

The skill operates relative to a repository root path provided by the user or inferred from context. All file paths in specs and test files are **relative** to this root. The agent must always confirm the target repository before starting work.

Test project convention: typically named `<SolutionName>.UnitTests` or `<SolutionName>.Tests`, located at `src/<TestProject>/`. If not found, ask the user for the correct test project location.

---

## Edge Cases & Special Handling (continued from previous section)

### NSubstitute `.Returns(value1, value2)` Cycling CAUTION

When a test base class constructor sets up mocks with multiple return values (`.Returns(val1, val2, ...)`), NSubstitute cycles through them on successive calls. This creates hidden inter-test dependencies because the behavior depends on call order across tests. Instead: configure mock returns per-test using helper methods or inline setup.

| Pattern | Risk | Recommendation |
| ------- | ---- | -------------- |
| `mock.Method().Returns(val1);` | None — safe for shared fixtures | ✅ Acceptable in constructor |
| `mock.Method().Returns(val1, val2);` | ⚠️ First call returns val1, second returns val2 — test-dependent | ❌ Move to per-test setup |
| `mock.ReceivedCalls()` inspection with LINQ | ⚠️ Can detect state leakage if not careful | Use sparingly; prefer explicit `Received(1)` assertions |

| Scenario | Handling Procedure |
| --- | --- |
| Target class has no constructor dependencies | Create tests without mocks; use inline fixture data directly. Document that mocking was unnecessary. |
| Target class depends on `DateTime.Now` / `Guid.NewGuid()` | Flag as CAUTION in analysis phase. Suggest introducing an `ITimeProvider` interface or similar abstraction rather than testing with time-sensitive assertions. |
| Sealed classes used as dependencies (no interface) | Cannot be mocked with NSubstitute. Options: (a) ask user to introduce an interface, (b) create a real fake/stub class in the test project, (c) skip those scenarios and note coverage gap. Present options to user for decision. |
| Static methods or singletons | Cannot be unit-tested directly. Flag as architectural concern; recommend wrapping static calls behind interfaces or using the Service Locator pattern. Skip these tests unless user explicitly requests wrapper creation. |
| Tests requiring database access | These are integration tests, not unit tests. Recommend moving them to a separate IntegrationTests project and flagging this out of scope for `cs-unit-test`. |
| Very large target class (>50 public methods) | Split into multiple test plan batches. Start with core/primary methods first. Ask user: "This class has 60+ public methods. Should I start with the most critical ones (X, Y, Z)?" |
| Target method uses `params` arrays or `object` types | Use explicit argument values in Arrange; avoid relying on NSubstitute's ArgMatcher flexibility for object-type parameters — be specific. |
| Tests need shared setup across many scenarios | Consider a base fixture class or factory method within the test class, but ensure each test still creates its own SUT instance to maintain isolation. |
---

### Custom Assertion Helper Guidelines


**Custom assertion methods with >5 parameters** — Helper assertions like `AssertTimeSpreadBooking(actual, request1, product1, result1, bookingInfo, ...)` hide what's being verified. When a test fails inside such a helper, you can't tell which specific condition failed without reading the method body.

Guideline: Custom assertion helpers are acceptable when they:
- Have ≤3 parameters that are conceptually related
- Each assert one logical concept
- Follow naming like `AssertFirstLegContract()`, `AssertPricingResult()`

Reject custom assertions when they:
- Require passing unrelated objects just to set up the assertion context
- Contain branching logic (`if (isNearLeg) { ... } else { ... }`)
- Assert more than 5 distinct conditions in a single call

For complex scenarios with many assertions, prefer inline FluentAssertions over extracting into helper methods — readability of individual tests matters more than DRY.

## Anti-Patterns to Avoid (Never Do These)

| Anti-Pattern | Why It's Bad | Correct Alternative |
| ------------ | ------------ | ------------------- |
| **Multiple Act tasks in one test** | You can't guarantee all Asserts execute after first failure; hard to identify which action caused the issue | Use `[Theory]` with `InlineData` for each scenario, or create separate `[Fact]` methods — see MS docs "Avoid multiple Act tasks" |
| Testing private methods directly | Breaks encapsulation; tests become brittle | Test through public API surface only |
| Using `[SetUp]` / `[OneTimeSetUp]` xUnit equivalent `ITestFixture<T>` with mutable state | Causes test order dependency and flakiness | Create fresh fixtures per test via constructor or local variables |
| Asserting implementation details (e.g., verifying exact number of mock calls for internal logic) | Tests break when refactoring internals that don't change behavior | Only assert on observable outcomes and externally visible interactions |
| Mixing xUnit `Assert.*()` with FluentAssertions in same test | Inconsistent style, harder to read | Use ONLY FluentAssertions throughout the entire project |
| Testing getters/setters without business logic | Adds no value; tests compiler behavior not your code | Skip trivial properties; test methods with actual logic |
| Using random values in assertions (`result.Should().NotBeNull()`) where a specific value is expected | Weak assertion — could pass by accident | Assert on specific, meaningful values |
| Long tests (>50 lines of Arrange) | Hard to read; likely testing too much | Extract complex fixture setup into private helper methods (named clearly, e.g., `ArrangeServiceWithValidOrder()`) |
| Sleeping/waiting in unit tests (`Thread.Sleep`, `Task.Delay`) | Flaky and slow | Use mockable timer/time provider or arrange timing-sensitive behavior via dependency injection |

---

## Best Practices

1. **Single agent, foreground only**: Every phase is executed directly by this skill's instructions. No sub-agents, no background threads.
2. **One target class at a time**: Do not interleave multiple test classes' files. Complete one target before starting another.
3. **Ask for name if unclear**: Never guess which class to test — prompt the user when the request is ambiguous.
4. **Document every deviation**: If implementation deviates from the approved plan, record it in `test-plan.md` and revert status to `PLANNED`.
5. **Compile after every batch**: Never accumulate N tests' worth of changes and compile only once. Build after EVERY atomic file edit in Phase 5 to isolate failures.
6. **Git-aware**: Use `git log`, `git blame` for evolutionary context when available (e.g., understand why a seemingly odd error path exists).
7. **Single assertion library, no exceptions**: Use ONLY FluentAssertions throughout the entire project — no raw `Assert.*` calls, NO custom `.ShouldBe()` wrapper extensions, and no mixing of xUnit assertions alongside FluentAssertions in the same test or even across different tests. If your codebase has existing mixed patterns, flag this as a systematic issue to fix separately; new tests must use one consistent approach.
8. **NSubstitute for all mocks**: No hand-rolled fakes unless absolutely necessary (sealed third-party class with no interface). Document why NSubstitute couldn't be used.
9. **AAA structure always enforced**: One Act statement. Clear Arrange/Act/Assert sections with comment separators.
10. **Descriptive naming convention**: `<MethodName>_ShouldReturnX_WhenCondition` or equivalent — pick one style and apply consistently across ALL tests in the project. Three valid conventions exist; never mix them.
11. **Realistic vs minimal test data trade-off**: For domain-specific tests where exact values carry business meaning (e.g., financial amounts, currency codes, pricing profiles), using realistic values is defensible even though it makes failures more verbose. Use minimal inputs (`0`, `""`) for pure logic/edge-case tests. The key distinction: if a wrong value means "wrong business result" (not just "wrong implementation"), use realistic data.
11. **Read before every edit**: This is not optional. Every `edit` operation must be preceded by at least one fresh `read` of the target file within the same turn or immediately before. Stale snapshots cause silent data loss.
12. **Fail-fast compilation after each test batch**: Never accumulate changes and compile only once. Build after EVERY atomic change in Phase 5 to isolate failures to a single test or scenario.
13. **Never touch auto-generated files**: `.g.cs`, Designer.cs, Source Generator output — these are ephemeral artifacts. If a generated file appears in scope, redirect to developer-authored code.
14. **Test project separation**: Tests should live in a separate assembly from production code with no runtime dependencies on the test framework (xUnit is dev-only).
15. **XML doc comments on every test method**: Every `[Fact]` and `[Theory]` method MUST have an `/// <summary>` block that describes: (a) which behavior under test is being verified, and (b) what the expected result or exception is. This makes it immediately clear to anyone reading the test suite what contract each test enforces — especially when tests fail and developers need to understand intent without tracing through Arrange/Act/Assert.

    ```csharp
    /// <summary>
    /// Tests that CreateUnwindOffsettingProduct clones the existing swap with quantities proportionally reduced
    /// and reverses its Buy/Sell direction (Buy→Sell, Sell→Buy).
    /// Expected: cloned product with opposite direction and sum ≈ 250 units.
    /// </summary>
    [Fact]
    public void CreateUnwindOffsettingProduct_ValidInput_ReturnsClonedProductWithOppositeDirection()
    {
        // ...
    }
    ```
16. **Inline builder setup instead of dedicated helpers for few-field builders**: When a builder only sets 3 or fewer fields, do NOT extract it into a `BuildXxx` helper method — write the builder chain inline inside each test. The overhead of a private method call outweighs the benefit when there are only 2-3 `.With...()` calls; developers should be able to see exactly what values flow into the SUT without scrolling away from the Arrange section.

    ✅ Preferred (inline):
    ```csharp
    var tradeNotionalChange = new TradeNotionalChangeBuilder()
        .WithEffectiveDate(DateTime.Today.AddDays(-1))
        .WithOutstandingNumberOfUnits(250m)
        .WithChangeInNumberOfUnits(750m)
        .Build();
    ```

    ❌ Anti-pattern (unnecessary helper):
    ```csharp
    var tradeNotionalChange = BuildTradeNotionalChange(
        effectiveDate: DateTime.Today.AddDays(-1),
        changeInNumberOfUnits: 750m,
        outstandingNumberOfUnits: 250m);
    // ... requires scrolling to find what values are actually set ...
    ```

    Exception: extract into a helper when the builder sets **4+ fields**. For parametrizing over 2-3 discrete values, prefer `[Theory]` + `[InlineData(...)]` — it keeps everything inline without needing a separate `MemberData` property or helper method.
17. **No conditional logic in test assertions**: Never use ternary operators (`? :`), `if`, `switch`, loops, or any branching inside tests. If the expected value depends on input data, pass it as an additional parameter via `[Theory]` + `[InlineData(a, b)]`. A bug in test-side branching can silently mask production defects — every assertion must be a direct comparison against known, explicit fixture data.

    ❌ Anti-pattern (conditional in Assert):
    ```csharp
    result.BuySell.Should().Be(originalDirection == BuySellEnum.Buy ? BuySellEnum.Sell : BuySellEnum.Buy);
    // BUG: if ternary logic is wrong, test passes incorrectly and masks real failures
    ```

    ✅ Preferred (data-driven):
    ```csharp
    [Theory]
    [InlineData(BuySellEnum.Buy, BuySellEnum.Sell)]
    [InlineData(BuySellEnum.Sell, BuySellEnum.Buy)]
    public void Test_WhenUnwindCalledWithDirection_ReturnsOppositeDirection(
        BuySellEnum originalDirection,
        BuySellEnum expectedDirection)
    {
        // ...
        result.BuySell.Should().Be(expectedDirection);
        // No branching — expectedDirection comes from test data
    }
    ```
18. **Assert individual collection elements, not just sums or counts**: When the SUT returns a collection whose values depend on per-element computation (e.g., proportional splitting, rounding), assert each element individually rather than only asserting `.Sum()` or `.Count()`. A passing sum check masks bugs in per-element distribution — two completely different arrays can have identical totals.

    ❌ Anti-pattern (only checks total):
    ```csharp
    result.Quantities.Sum().Should().BeApproximately(250m, 1m);
    // Passes even if actual was [0, 0, 250] instead of expected [62.5, 87.5, 100]
    ```

    ✅ Preferred (verifies distribution):
    ```csharp
    result.Quantities[0].Should().BeApproximately(62.5m, 1m);
    result.Quantities[1].Should().BeApproximately(87.5m, 1m);
    result.Quantities[2].Should().BeApproximately(100m, 1m);
    // Fails immediately if any element is wrong — precise failure location
    ```

    Exception: sum-only assertions are acceptable when the collection has only one or two elements and the operation is inherently aggregate-based (e.g., `result.Count.Should().Be(3)`).
19. **Do not merge `[Fact]` tests with variable-length array inputs into a single `[Theory]`**: `[InlineData(new T[] { ... })` is invalid because array initializers are NOT compile-time constants — xUnit's data attribute system requires each InlineData argument to be itself a constant expression. The `params object[]` workaround also fails when different test rows have **different numbers of elements** (e.g., 1 element vs 3 elements). In these cases, keep separate `[Fact]` methods instead of forcing a Theory.

    ❌ Anti-pattern (invalid syntax):
    ```csharp
    [Theory]
    [InlineData(new decimal[] { 0m }, "zero quantity")]
    [InlineData(new decimal[] { 250, 350, 400 }, "three periods")] // COMPILE ERROR!
    public void Test_WhenQuantitiesAreVaryingLength_ThenHandlesCorrectly(decimal[] quantities, string label)
    {
        // ...
    }
    ```

    ✅ Preferred (separate Facts for fundamentally different input shapes):
    ```csharp
    [Fact]
    public void CreateUnwindOffsettingProduct_ZeroTotalQuantity_ThrowsArgumentException()
    {
        var existingProduct = new CustomQuantityFinancialCommoditySwapBuilder().Build();
        existingProduct.Quantities = [0m]; // zero quantity — single element array
        // ... Act & Assert with specific exception message ...
    }

    [Fact]
    public async Task CreateUnwindOffsettingProduct_OutstandingUnitsDoNotMatchCalculatedSum_ThrowsArgumentException()
    {
        var existingProduct = new CustomQuantityFinancialCommoditySwapBuilder().Build();
        existingProduct.Quantities = [250, 350, 400]; // three unequal periods
        // ... Act & Assert with different exception message ...
    }
    ```

    **When merging IS acceptable**: Both scenarios have the same input shape (same number of parameters) and produce the same type of result. Use `[Theory]` only when you can express all varying values as flat constant arguments per row.

---

**Code coverage is NOT quality** — A high percentage (e.g., 95%+) does not imply high-quality tests. The last 10% of edge cases may require disproportionate effort with diminishing returns. Focus on testing behavior and scenarios that matter to the business, not achieving arbitrary coverage targets.

---

## Script Locations

When scripts are needed for analysis (e.g., dependency extraction from source files, test coverage gap identification), they should follow the Python Script Library Management Instructions from AGENTS.md:

- Primary location: `~/.pi/agent/skills/cs-unit-test/scripts/`
- Global fallback: `~/.pi/agent/scripts/`
- Index documentation: `~/.pi/agent/skills/cs-unit-test/references/index.md` (created if missing)
