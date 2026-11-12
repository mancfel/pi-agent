# Builder Pattern Conventions (Fluent API)

These conventions define the standard approach for implementing fluent builder classes in C#. They generalize well-established patterns used across large-scale codebases with hundreds of builders and thousands of model types.

## Builder Class Structure

```csharp
public class EntityNameBuilder : Builder<EntityModel, EntityNameBuilder>
{
    public override EntityNameBuilder WithTestValues()
    {
        // Initialize scalar/primitive defaults
        Entity.Property1 = "default_value";
        Entity.Property2 = 42;
        
        // ✅ CRITICAL: Initialize every complex/nested property
        Entity.NestedProperty = new NestedEntityBuilder().WithTestValues();
        
        return this;
    }

    protected override void Init()
    {
        // Reserved for future initialization logic (currently empty)
    }
}
```

### Key Structural Rules

- **Inherit from a generic base class** — `Builder<TEntityModel, TSelf>` provides common functionality.
- **Always use the inherited `Entity` property** to access model data — never declare private entity fields on the builder itself.
- **One class per file** — builders are single-class files with no partial classes or nested types.
- **Namespace mirrors the domain structure** of the corresponding models being built.

## Setter Method Patterns

### 1. Scalar / Primitive Setters

For simple value types (`string`, `int`, `double`, enums, nullable primitives):

```csharp
public EntityNameBuilder WithId(string value) {
    Entity.Id = value;
    return this;
}
```

Direct assignment to `Entity.Property`. Return `this` for fluent chaining.

### 2. Primitive Collection Setters — `params T[]` (Preferred)

For properties typed as `List<T>` where `T` is a primitive type:

```csharp
// Property: public List<string> Countries { get; set; }
public EntityNameBuilder WithCountries(params string[] value) {
    Entity.Countries = [.. value];   // collection expression — null-safe spread
    return this;
}
```

**Caller usage:**
```csharp
builder.WithCountries("US", "GB", "FR");   // natural, no wrapper
builder.WithCountries();                    // empty list
```

**Why `params T[]` over direct `List<T>` assignment:**
- **Ergonomics** — callers write `"A", "B"` instead of `new List<string>{"A","B"}`.
- **Null safety** — `[.. value]` converts null/empty to an empty collection.
- **Encapsulation** — the builder owns the internal list; callers only see a read-only array.

### 3. Complex/Nested Entity Setters — `Func<Builder, Builder>` Delegate (Preferred)

For properties whose types are complex or nested entities:

```csharp
public EntityNameBuilder WithCancel(
    Func<MxML_CancelBuilder, MxML_CancelBuilder> builder) {
    Entity.Cancel = builder?.Invoke(new MxML_CancelBuilder());
    return this;
}
```

**Caller usage:**
```csharp
contractBuilder.WithCancel(c => c
    .WithCancellationReason("Test")
    .WithCancellationDate("20261231"));
```

**Why Func delegates over direct object assignment:**
- **Encapsulation** — callers interact only with builders; raw model types stay internal.
- **Inline composition** — no need to pre-build a nested entity in a separate statement.
- **Null safety** — `builder?.Invoke(...)` returns null if the delegate is absent (never throws).
- **Readability** — test code stays compact and expressive.

### 4. Complex Entity Collections (`List<TEntity>`) — Unified Func Approach

For collection properties of complex entities, use the same single-delegate pattern:

```csharp
// Property: public List<MxML_TradeView> TradeViews { get; set; }
public EntityNameBuilder WithTradeViews(
    Func<MxML_TradeViewBuilder, MxML_TradeViewBuilder> builder) {
    Entity.TradeViews = builder?.Invoke(new MxML_TradeViewBuilder());
    return this;
}
```

The base class provides an **implicit conversion operator** that handles `List<TEntity>` assembly via a `.New()` method on each sub-builder.

**Caller usage — multiple items:**
```csharp
contractBuilder.WithTradeViews(v => v
    .WithViewName("P&L")
    .WithViewType("summary")
    .New()                              // finalize "P&L", start next item
        .WithViewName("Risk")
        .WithViewType("detail"));
```

Each `.New()` call appends the configured entity to the internal collection and returns a fresh builder instance. When the lambda completes, the implicit conversion assembles all tracked items into `List<TEntity>`.

## Sub-Builder Creation Chain (Mandatory)

When writing a new builder that references nested entities via Func delegates, **every sub-builder class must exist**. Never leave gaps in the builder chain.

**Rule: Build from leaf inward.** Create dependencies first, then parent builders:

1. Leaf builder with no dependencies → create first
2. Builder depending on leaves → create second  
3. Parent builder referencing those → created last

**Verification checklist before committing:**
- [ ] All `Func<TSubEntityBuilder, ...>` parameter types have corresponding `<TSubEntityBuilder>.cs` files present.
- [ ] Transitive dependencies are satisfied — recursively check each sub-builder's own Func parameters.
- [ ] No circular builder dependencies (A needs B which needs A).

## Test Initialization Rule

Every complex/nested property **MUST be initialized in `WithTestValues()`**:

```csharp
public override EntityNameBuilder WithTestValues() {
    // Scalar defaults...
    
    // ✅ Every TProp with a corresponding builder MUST be initialized:
    Entity.NestedProperty = new NestedEntityBuilder().WithTestValues();
    
    return this;
}
```

This prevents `NullReferenceException` when tests call `.Build()` without explicitly setting every nested property. The pattern ensures default entities are always fully populated, even if not all leaf properties are individually set by the caller.

## Anti-Patterns to Avoid

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| Declare private entity fields on builders | Always use inherited `Entity` property |
| Accept raw model objects in setters (`WithX(MxML_Cancel value)`) | Use Func delegate: `WithX(Func<MxML_CancelBuilder, MxML_CancelBuilder> builder)` |
| Bare `.Invoke(delegate)` without null check | Use `builder?.Invoke(new Builder())` for safe invocation |
| Leave sub-builders uncreated when referenced | Build leaf inward; verify all dependencies exist before committing |
| Initialize only some complex properties in WithTestValues() | Initialize ALL of them — every nested entity gets its own builder + WithTestValues() |
| Pre-construct nested entities outside the setter chain | Compose inline via Func delegates in a single expression |
