# arch-doc-extractor — Architecture Documentation Extractor for C#/.NET

Quick-start guide for the `arch-doc-extractor` pi agent skill.

## What It Does

Generates comprehensive `ARCHITECTURE.md` documentation from any C#/.NET codebase by combining:
1. **Deterministic structural extraction** (regex + brace-balanced parsers on `.csproj`, `.sln`, `Program.cs`, and all `.cs` files)
2. **Agent-synthesized prose** (the pi-agent reads structured JSON and writes ARCHITECTURE.md using its own model)
3. *(Optional)* HTTP API mode — fully automated LLM synthesis via OpenAI-compatible endpoint

## Quick Start (Agent-Synthesized — Recommended)

```bash
# Step 1: Run extraction only (no LLM needed)
python scripts/extract_arch.py --target-dir "D:/my-dotnet-solution" --no-llm --verbose

# Step 2: The pi-agent reads extract_data.json, follows references/output-template.md,
#         and writes ARCHITECTURE.md using its own model.
```

**Why this approach?** Zero extra configuration. Uses the same model already configured in your pi-session. No API keys, no separate Ollama endpoints required.

## Coverage Matrix

| Section | Extraction Method |
|---------|------------------|
| Solution Overview, Project Structure | Parse `.sln` + `.csproj` XML |
| Dependency Graph | Disk scan of `<ProjectReference>` tags across all `.csproj` files |
| Architecture Layers | Namespace convention analysis (`*.Domain.*`, `*.Application.*`) |
| Design Patterns (Repository, CQRS/MediatR, UnitOfWork) | Interface/implementations pairs, generic constraints, attribute detection |
| DI Container Analysis | Brace-balanced extraction of ALL `public static IServiceCollection Add...` extension methods |
| Middleware Pipeline | `app.Use*()` / `app.Map*()` calls in Program.cs |
| Data Access Layer | DbContext subclass discovery + `OnModelCreating` body extraction |
| API Surface | `[ApiController]`, Minimal APIs (`MapGet/Post`), gRPC services, Blazor components |
| Test Architecture | Test project naming convention + package refs + test attributes |
| **Test Patterns** | A-A-A strength via comment markers, section spacing, Moq `.Setup().Returns()`, FluentAssertions `.Should().Be()` — strong/moderate/weak |
| **Test Naming Conventions** | Classify dominant style: xunit_convention, descriptive_sentence, pascal_separated — expanded C# indicators (`_when`, `_given`, `creates`, `returns`, etc.) |
| **Class Inheritance Hierarchies** | Build base→derived trees; report top 15 hierarchies by derived count |
| **Namespace-Location Correlation** | Map namespace prefixes to file paths → reveals "where files live" rules |
| External Packages (with CPM support) | `<PackageReference>` parsing with `Directory.Packages.props` inheritance chain |
| Configuration System | `IOptions<T>`, `builder.Configuration.GetSection("...")` patterns |
| Health Checks & Monitoring | `IHealthCheck` implementations, health check middleware |
| Background Services | `BackgroundService` subclasses, Hangfire, Quartz.NET registrations |
| DDD Primitives Assessment | Entity class signatures → LLM semantic evaluation of rich vs anemic domain |
| OpenTelemetry Observability | `AddOpenTelemetry()` registration, ActivitySource declarations, exporter targets |
| Event-Driven Architecture/Messaging | MassTransit/Rebus/NServiceBus packages + `IConsumer<T>` inventory + outbox/inbox patterns |

## Edge Cases Handled Automatically

1. **CPM Version Override**: `VersionOverride="..."` on `<PackageReference>` takes priority over central versions in `Directory.Packages.props`.
2. **Solution Folder Wildcards**: Dependency resolution uses disk scan of `.csproj` files as primary source (not just `.sln` parsing).
3. **Multi-line DI Extensions**: Brace-balancing parser captures full method body even with nested lambdas and if-blocks.
4. **Token Budget Limits**: DI registrations capped at 150 lines, middleware at 80 lines — prioritized by architectural significance.

## CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--target-dir <path>` | *(required)* | Root directory of the .NET solution |
| `--output <path>` | `<target>/ARCHITECTURE.md` | Output file path (Workflow B only) |
| `--token-budget-di <lines>` | 150 | Max DI registration lines passed to LLM synthesis |
| `--entity-samples <count>` | 5 | Entity classes sampled for DDD evaluation |
| `--no-llm` | **Enabled** | Produce raw JSON only (`extract_data.json`) — agent does synthesis |
| `--verbose` | Disabled | Print per-phase progress to stderr |

> **Workflow B flags** (only when omitting `--no-llm`): `--llm-api-base`, `--llm-model`, `--llm-key`. The script auto-detects `$PI_MODEL` and `$PI_API_BASE` from pi-agent environment variables.

## Architecture

```
SKILL.md                          ← Agent instructions (execution model, invocation)
references/
├── output-template.md            ← ARCHITECTURE.md section template with {{placeholders}}
scripts/
└── extract_arch.py               ← Core extraction engine (Phases A–G + optional Phase H: LLM)
README.md                         ← This file
```

**Script phases:**
- **Phase A**: Solution Discovery — `.sln`, `.csproj`, CPM resolution
- **Phase B**: Entry Point & Extension Discovery — Program.cs, DI extension methods (brace-balanced), middleware calls
- **Phase C**: Namespace Architecture Analysis — layer classification from namespace patterns
- **Phase D**: Pattern Detection — Repository, MediatR/CQRS, EF Core DbContext, attributes
- **Phase E**: Test Structure Analysis — test frameworks, mocking libraries
- **Phase F**: External Dependencies Catalog — semantic package categorization with CPM support
- **Phase G**: Observability & Messaging — OpenTelemetry + MassTransit/RabbitMQ/Azure Service Bus detection
- **Phase H** (optional): LLM Synthesis — structured data → human-readable ARCHITECTURE.md via API

## Testing Against Real Repositories

The script was tested against `conventions-extractor` (.NET 10 solution) and produced:
- ✅ Correct .sln and .csproj discovery
- ✅ xUnit test framework detection
- ✅ Namespace pattern extraction
- ✅ Package version resolution (including legacy non-CPM projects)

For best results, run on a real Clean Architecture or layered API project to see the full layer classification in action.
