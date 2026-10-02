# Architecture Documentation — {{solution_name}}

> **Generated**: {{date_generated}}  
> **Extraction tool**: `arch-doc-extractor` ({{tool_version}})  
> **Source commit/branch**: {{git_branch_or_sha}}  
> **Solution root**: {{repo_relative_path}}  

---

## 1. Solution Overview

- **Solution name**: {{solution_file_name}}
- **Total projects**: {{project_count}}
- **Target frameworks**: {{list_frameworks}}
- **Architecture style detected**: {{detected_style}} (e.g., Clean Architecture, Layered, Modular Monolith, Microservices)
- **Primary API type**: {{api_type}} (REST/Minimal APIs/gRPC/Blazor/mixed)

### Project Inventory

| # | Project Name | Path | SDK Type | Target Framework | Output Type | Purpose |
|---|-------------|------|----------|------------------|-------------|---------|
| 1 | {{name}} | {{path}} | {{sdk}} | {{tfm}} | {{output_type}} | {{inferred_purpose}} |

---

## 2. Dependency Graph

### Project-to-Project Dependencies

```mermaid
graph LR
    {{mermaid_project_deps}}
```

> **Note**: If no `Directory.Packages.props` was found, packages are managed inline in each `.csproj`.  
> If CPM is active: inheritance chain = {{cpm_inheritance_chain}}. Effective versions resolved from {{cpm_file_path}}.

---

## 3. Architecture Layers

Detected architectural boundaries based on namespace conventions and project organization:

| Layer | Namespace Pattern | Projects | Description |
|-------|------------------|----------|-------------|
| Domain | `*.Domain.*` | {{domain_projects}} | Core business entities, value objects, domain events |
| Application | `*.Application.*` | {{app_projects}} | Use cases, CQRS handlers (MediatR), DTOs, validators |
| Infrastructure | `*.Infrastructure.*` | {{infra_projects}} | EF Core DbContext, external APIs, repositories, messaging brokers |
| Presentation | `*.Presentation.*` or `*.API.*` | {{present_projects}} | Controllers, Minimal API endpoints, gRPC services, Blazor components |

### Layer Verification

- **Clean Architecture compliance**: {{compliance_status}} — {{compliance_note}}  
  *(Checks: Domain has no project references to outer layers; Application depends only on Domain and self.)*
- **Circular dependencies detected**: {{circular_deps_list_or_none}}
- **Namespace convention adherence**: {{adherence_score}}% of projects follow the inferred naming pattern.

---

## 4. Design Patterns Detected

### Inversion of Control / Dependency Injection

| Pattern | Evidence | Projects Affected |
|---------|----------|-------------------|
| Service Locator via DI Container | `builder.Services.Add*()` registrations in Program.cs | {{projects}} |
| Repository Pattern | `IRepository<T>` interfaces + implementations | {{repos}} |
| UnitOfWork | `UnitOfWork` class with multiple repo properties | {{uow_projects}} |
| Factory | Classes implementing or named `*Factory`, `IObjectFactory` | {{factory_classes}} |
| Strategy | Interface + multiple concrete implementations, selected at runtime | {{strategy_interfaces}} |
| Mediator (CQRS) | MediatR `IMediator` injection + `IRequestHandler<Command, Result>` classes | {{cqrs_count}} handlers across {{cqrs_projects}} |

### Other Patterns

- **Singleton services**: {{singleton_services_list}} — registered via `.AddSingleton<T>()` or framework singletons (`ILogger`, `IConfiguration`)
- **Scoped services**: {{scoped_count}} registrations — typically per-request HTTP contexts
- **Transient services**: {{transient_count}} registrations — created on each injection point
- **EF Core conventions detected**: {{ef_conventions}} — e.g., Fluent API configurations in `OnModelCreating`, data annotations, convention-based mapping

---

## 5. DI Container Analysis

### Service Registration Summary

| Lifetime | Count | Notable Registrations |
|----------|-------|----------------------|
| Transient | {{count}} | {{examples}} |
| Scoped | {{count}} | {{examples}} |
| Singleton | {{count}} | {{examples}} |
| AddDbContext<T> | {{count}} | {{context_names}} (lifetimes: {{context_lifetimes}}) |

### Key Extension Methods Found

The following custom extension methods were detected across source files:

```csharp
// {{extension_method_name_1}} — located in {{file_path}}
{{extracted_code_block_1}}

// {{extension_method_name_2}} — located in {{file_path}}
{{extracted_code_block_2}}
```

> **Note**: The script extracted up to `--max-extension-methods` extension methods. More may exist but were truncated for context budget.

---

## 6. Middleware Pipeline

Detected middleware order from `Program.cs`:

| # | Middleware Component | Type | Position (relative) | Purpose |
|---|---------------------|------|--------------------|---------|
| 1 | {{middleware_1}} | Use* / Map* | Early | {{purpose}} |
| 2 | {{middleware_2}} | Use* / Map* | Middle | {{purpose}} |
| ... | ... | ... | ... | ... |
| N | {{middleware_N}} | Use* / Map* | Late | {{purpose}} |

### Critical Ordering Notes

- **Authentication → Authorization**: {{authz_ordering_status}} — `UseAuthentication()` is placed before `UseAuthorization()`.  
- **Exception handling**: Exception handler middleware appears at position #{{position}} (should be early for global catch).  
- **Minimal API endpoints**: Detected via {{method}} — `app.MapGet/Post/Delete/Put()` or route groups with `MapGroup()`.

---

## 7. Data Access Layer

### DbContext Classes

| Context Name | Database Provider | Key Configurations | Migrations Present? |
|-------------|------------------|-------------------|--------------------|
| {{context_1}} | {{provider}} | Fluent API, data annotations, convention overrides | Yes / No |

### Repository Pattern Usage

- **Repositories implemented**: {{repo_count}} across {{repo_projects}}
- **Base repository interface**: {{base_interface_name_or_none}}
- **DbContext-based access only** (no explicit repositories): {{yes_if_true}} — entities accessed directly via `DbSet<T>` properties

### Migration & Seeding Strategy

- **EF Core migrations folder present**: {{yes/no}} at `{{migration_folder_path}}`
- **Data seeding detected**: {{seeding_method}} — e.g., `OnModelCreating` seed calls, separate seeder classes, or external tools.

---

## 8. API Surface

### Transport Layer Classification

| Transport | Technology | Endpoints/Services Detected | Projects |
|-----------|-----------|-----------------------------|----------|
| REST/JSON | Controllers (`[ApiController]`) | {{controller_count}} controllers with {{action_count}} actions | {{projects}} |
| REST/JSON | Minimal APIs (Lambda-based) | {{minimapic_endpoints}} endpoint registrations | {{projects}} |
| gRPC | .proto contracts + GrpcServiceBase | {{grpc_service_count}} services | {{projects}} |
| Blazor Server/WASM | Razor components | {{razor_file_count}} `.razor` files, render mode: {{render_mode}} | {{projects}} |

### API Versioning

- **Strategy**: {{versioning_strategy_or_none}} — e.g., URL path (`/v1/resource`), query string (`?api-version=1.0`), header (`X-API-Version`)
- **Versioned endpoints detected**: {{yes/no}} via `[ApiVersion("1.0")]` attributes or route groups

---

## 9. Test Architecture

| Aspect | Detail |
|--------|--------|
| Test framework | {{framework}} (detected from package refs + attribute usage) |
| Number of test projects | {{test_project_count}} |
| Mocking library | {{mock_lib}} (Moq, NSubstitute, FakeItEasy, or none) |
| Test data generation | {{data_gen_tool}} (Faker.NET, Bogus, manual factories) |
| Test organization pattern | {{pattern}} — e.g., xUnit `[Fact]`/`[Theory]`, NUnit `[Test]`/`[TestCase]`, MSTest `[TestMethod]` |
| Integration tests present | {{yes/no}} — detected via HttpClient/WebApplicationFactory patterns |

### Test Code Examples

```csharp
// Sample test from {{test_project_name}}
{{sample_test_code_block}}
```

---

## 10. External Packages Catalog

Packages grouped by semantic category:

| Category | Packages | Version(s) | Purpose Inferred |
|----------|---------|-----------|------------------|
| Logging | Serilog, Serilog.Sinks.Console | {{versions}} | Structured logging to console/file |
| Auth & Security | Microsoft.AspNetCore.Authentication.JwtBearer | {{version}} | JWT authentication for API endpoints |
| Mapping | AutoMapper, Mapster, or Mapperly | {{version}} | Object-to-object DTO mapping |
| Validation | FluentValidation | {{version}} | Request validation via `AbstractValidator<T>` |
| Caching | StackExchange.Redis, IMemoryCache | {{version}} | Distributed/in-process caching |
| Messaging/EDA | MassTransit + RabbitMQ (or Azure Service Bus) | {{version}} | Asynchronous event-driven communication |
| Observability | OpenTelemetry.Exporter.Prometheus/Jaeger | {{version}} | Metrics and distributed tracing |

> **Total unique packages**: {{total_packages}}  
> **Central Package Management active**: {{yes/no}} — inheritance chain: {{chain_description}}

---

## 11. Configuration System

- **Configuration source hierarchy**: `appsettings.json` → `appsettings.{Environment}.json` → Environment variables → CommandLine  
- **IOptions<T> pattern usage**: {{options_usage_status}} — strongly-typed configuration classes bound via `builder.Configuration.GetSection("...")`  
- **Secrets management detected**: {{secrets_status}} — e.g., User Secrets (`dotnet user-secrets`), Azure Key Vault integration, or external secret store.

---

## 12. Cross-Cutting Concerns

| Concern | Technology / Approach | Location |
|---------|----------------------|----------|
| Logging | Serilog (via `UseSerilog()`) or Microsoft.Extensions.Logging | Program.cs host builder; sink configurations in appsettings.json |
| Authentication/Authorization | JWT Bearer, Cookie Auth, Azure AD, IdentityServer/Duende | Program.cs authentication middleware setup |
| Error Handling | Global exception handler middleware, IExceptionHandler<T>, or custom middleware | Exception handling pipeline configuration |
| Caching | In-memory (`IMemoryCache`) or distributed (`IDistributedCache` + Redis) | DI registration via `AddMemoryCache()` or `AddStackExchangeRedisCache()` |

---

## 13. Health Checks & Monitoring

- **Health check packages**: {{health_check_packages_or_none}} — e.g., `AspNetCore.HealthChecks.UI`, `AspNetCore.HealthChecks.SqlServer`  
- **Custom health checks implemented**: {{custom_health_count}} classes inheriting from `IHealthCheck`  
- **Liveness/Readiness probes split**: {{probe_split_status}} — separate endpoints for Kubernetes liveness vs readiness, using tag-based filtering on `MapHealthChecks()`.

---

## 14. Background Services

| Service Type | Technology | Count | Description |
|-------------|-----------|-------|-------------|
| HostedService / BackgroundService | Native .NET | {{count}} | Classes inheriting from `BackgroundService` with `ExecuteAsync()` implementation |
| Hangfire Jobs | Hangfire (`AddHangfire()`) | {{count}} recurring/scheduled jobs detected in configuration |
| Quartz.NET Scheduler | Quartz.NET (`AddQuartz()`) | {{count}} job definitions found |
| MassTransit Consumers | MassTransit + broker | {{consumer_count}} classes implementing `IConsumer<T>` — asynchronous message processing |

---

## 15. gRPC Services (if applicable)

- **.proto file count**: {{proto_file_count}}  
- **gRPC service implementations**: {{grpc_service_count}} classes inheriting from `{Service}Base`  
- **Client projects consuming external gRPC**: {{client_projects_list_or_none}} via `GrpcChannel.ForAddress()`  

---

## 16. Blazor Architecture (if applicable)

- **Render mode**: {{render_mode}} — Server, WASM, or Hybrid  
- **Component count by type**: Server components: {{server_count}}, Shared components: {{shared_count}}  
- **Hosted solution pattern detected**: {{hosted_pattern_status}} — e.g., separate client/server projects with shared domain project  
- **State management approach**: {{state_mgmt_approach}} — e.g., cascading parameters, EventStream, Fluxor/Redux pattern, or simple DI services

---

## 17. DDD Primitives Assessment

> **Assessment method**: The LLM evaluated entity class signatures (public properties + public non-trivial methods) extracted from the Domain layer. This is a semantic assessment, not a regex-based count.

### Domain Richness Score: {{score}} / 5

| Entity Class | Public Properties | Non-Trivial Methods | Business Logic Indicators |
|-------------|------------------|--------------------|--------------------------|
| {{entity_1}} | {{prop_count}} | {{method_list}} | {{assessment_note}} — e.g., "Contains domain event raising and invariant validation" |
| {{entity_2}} | ... | ... | ... |

### Assessment Summary

- **Domain model type**: {{rich_or_anemic}} — {{explanation}}  
  *(Rich = entities contain behavioral methods with business logic; Anemic = entities are pure data classes with getters/setters only.)*
- **Value objects detected**: {{vo_count}} via base class inheritance or C# records with private constructors + factory methods
- **Aggregate roots identified**: {{aggregate_roots_list}} — entities that serve as entry points for aggregate operations
- **Domain events pattern**: {{domain_events_status}} — `_domainEvents.Add()` calls, `Raise()` methods, or domain event notification handlers

---

## 18. Observability & Telemetry

### OpenTelemetry Configuration

| Component | Status | Details |
|-----------|--------|---------|
| Distributed Tracing (`AddOpenTelemetry().WithTracing()`) | {{enabled/disabled}} | Exporter: {{exporter_target}} (Prometheus/Jaeger/Zipkin/OTLP) |
| Metrics Collection (`.WithMetrics()`) | {{enabled/disabled}} | Exporter: {{metrics_exporter}}, runtime instrumentation: {{runtime_instrumentation_status}} |
| Log Correlation with OTel | {{correlated/not_correlated}} | Serilog enriched via `Enrich.FromLogContext()` or native OTel log exporter |

### Custom Instrumentation

- **ActivitySource declarations**: {{activity_source_count}} classes declaring custom `ActivitySource` instances — indicates business-level span creation beyond framework auto-instrumentation.  
- **Manual `.Start()` calls detected**: {{manual_span_count}} — explicit span wrapping in domain/application code.

---

## 19. Event-Driven Architecture / Messaging

### Broker Technology

| Aspect | Detail |
|--------|--------|
| Library used | MassTransit / Rebus / NServiceBus / Direct SDK (Azure.Messaging.ServiceBus, RabbitMQ.Client) |
| Broker type | RabbitMQ / Azure Service Bus / Kafka / Amazon SQS / none (in-process only) |
| Connection configuration | appsettings.json section: `{{config_section_name}}` or environment variable: `{{env_var_name}}` |

### Message Inventory

| Direction | Count | Details |
|-----------|-------|---------|
| Consumers (`IConsumer<T>`) | {{consumer_count}} | Processing messages from broker queues/topics |
| Producers/Publishers | {{producer_locations}} | Classes calling `.Publish()` or `.Send()` via `IBus`/`IPublishEndpoint` injection |
| Message types defined | {{message_type_count}} | Record/class types used as message contracts (found in consumer generic type parameters) |

### Reliability Patterns

- **Outbox pattern**: {{outbox_status}} — MassTransit `EntityFrameworkOutbox`, custom transactional outbox, or absent  
  *(If present: guarantees event persistence before publish. If absent: at-least-once delivery only, no exactly-once guarantee for DB+event pairs.)*
- **Inbox pattern (deduplication)**: {{inbox_status}} — duplicate message prevention via processed messages table or library-built-in deduplication.

---

## 20. Package Management Strategy

| Aspect | Detail |
|--------|--------|
| Central Package Management (CPM) active | {{yes/no}} |
| CPM file location(s) | `{{Directory.Packages.props_path}}` in directory hierarchy: {{inheritance_chain}} |
| Directory.Build.props propagation | {{build_props_found}} at {{path}} — SDK types, target frameworks, global properties inherited from here |
| Version override usage | {{version_override_count}} packages use `<PackageReference ... VersionOverride="...">` to override central versions locally |

---

## 21. Configuration & Environment Strategy

- **Environment detection**: .NET standard environment-based configuration via `ASPNETCORE_ENVIRONMENT` variable  
- **Configuration providers used**: JSON (`appsettings.json`), Environment Variables, Command Line, Azure App Configuration (if detected)  
- **Secrets management**: User Secrets (dev only), Azure Key Vault integration, HashiCorp Vault, or no external secrets store  

---

## 22. Limitations & Caveats

- This document was generated by automated static analysis combined with LLM synthesis. It should be reviewed against the actual codebase for accuracy.
- Dynamic service registrations (e.g., reflection-based `.Add(typeof(Assembly).GetTypes())`) are not captured — only explicit registration calls are detected.
- Namespace convention inference is heuristic; architectural boundaries may differ from inferred layers if non-standard naming conventions are used.
- The DDD domain richness assessment is based on a sample of entity class signatures and represents an expert interpretation, not an absolute measurement.
- For large solutions (>50 projects), some sections may be truncated to fit within token budgets. Check `extract_data.json` for complete raw data.

---

*Document generated by arch-doc-extractor v{{version}} on {{timestamp}}.*  
*Source: {{git_branch_or_sha}}, repository root: {{repo_path}}.*
