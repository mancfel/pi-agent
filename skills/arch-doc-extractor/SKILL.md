---
name: arch-doc-extractor
description: Extracts comprehensive architectural documentation from C#/.NET codebases — solution structure, DI container, middleware pipeline, design patterns, API surface, test architecture, observability (OpenTelemetry), event-driven messaging (MassTransit/RabbitMQ/Azure Service Bus), and DDD domain richness assessment; produces ARCHITECTURE.md following output-template.md.
---

# Architecture Document Extractor Skill (`arch-doc-extractor`)

Use this skill to generate `ARCHITECTURE.md` from a C#/.NET codebase by combining deterministic structural extraction with LLM synthesis. This skill is designed for .NET solutions of any size — from simple layered APIs to modular monoliths with Clean/Onion architecture.

## Execution Model — Single Agent, Foreground Only

> Run every command directly. Do NOT spawn background processes or sub-agents for extraction.
>
> 1. Execute the Python wrapper script and wait for completion before proceeding.
> 2. Validate all output artifacts immediately after invocation.
> 3. Feed structured extraction data into an LLM prompt following the template in `references/output-template.md`.
> 4. Write the synthesized document as `<REPO_ROOT>/ARCHITECTURE.md`.
> 5. If the tool fails at any step, report the error and attempt manual fallback in the same session.

## Admitted Input States
- Any state — architecture extraction is independent of feature lifecycle states.
- Can run standalone or after `project-discovery` (which identifies C#/.NET as present).

## Prerequisites

| Requirement | Command | Fallback |
| ----------- | ------- | -------- |
| Python 3.8+ | `python --version` | Document failure; cannot proceed without Python for structural parsing |
| Target repository root path | Provided by user or inferred from context | Ask user before starting |

> **Note:** No external packages are required beyond Python standard library (`os`, `re`, `xml.etree.ElementTree`, `json`, `pathlib`). The script is self-contained.

## Invocation — Two Workflows

### Workflow A: Agent-Synthesized (Recommended for pi-agent)

The agent runs the extraction, reads `extract_data.json`, and synthesizes ARCHITECTURE.md using its own model. Zero extra configuration needed.

```bash
# Step 1: Run extraction only
python C:/Users/super/.pi/agent/skills/arch-doc-extractor/scripts/extract_arch.py \
    --target-dir "D:/projectRoot" \
    --no-llm \
    --verbose

# Step 2: Read extract_data.json, then synthesize ARCHITECTURE.md
#        following references/output-template.md as your guide.
```

### Workflow B: Fully Automated (Optional — HTTP API mode)

For CI/CD pipelines or when you want the script to call an LLM directly. Requires access to an OpenAI-compatible endpoint (Ollama, vLLM, OpenRouter, etc.).

```bash
python C:/Users/super/.pi/agent/skills/arch-doc-extractor/scripts/extract_arch.py \
    --target-dir "D:/projectRoot" \
    --output "D:/projectRoot/ARCHITECTURE.md"
# Defaults to http://localhost:11434/v1 + PI_MODEL env var if available.
```

### CLI Flags Reference

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--target-dir <path>` | *(required)* | Root directory of the .NET solution |
| `--output <path>` | `<target>/ARCHITECTURE.md` | Output file path (Workflow B only) |
| `--token-budget-di <lines>` | 150 | Max DI registration lines passed to LLM synthesis |
| `--token-budget-middleware <lines>` | 80 | Max middleware pipeline lines passed to LLM synthesis |
| `--entity-samples <count>` | 5 | Number of representative entity classes for DDD evaluation |
| `--no-llm` | **Enabled** | Default mode — produce JSON only; agent does synthesis inline |
| `--verbose` | Disabled | Print per-phase progress and warnings to stderr |

> **Workflow B optional flags** (only needed when omitting `--no-llm`):
> - `--llm-api-base <url>` — defaults to `$PI_API_BASE` or `http://localhost:11434/v1`
> - `--llm-model <name>` — defaults to `$PI_MODEL` env var, then `qwen2.5:7b`
> - `--llm-key <key>` — defaults to `$LLM_KEY` env var; empty for local Ollama

### Configuration Precedence

Configuration is resolved in this order (highest to lowest priority):

1. **CLI flags** — e.g., `--target-dir`, `--output`, `--token-budget-di`
2. **Environment variables**:
   - `ARCH_DOC_API_BASE` — OpenAI-compatible API base URL
   - `ARCH_DOC_MODEL` — Model name to use
   - `ARCH_DOC_API_KEY` — API key
3. **Defaults** as shown above

> **IMPORTANT**: Never include any credential in versioned artifacts or stdout logs. Add `.env` to the repository's ignore list if not already present.

## Extraction Phases

The Python script executes these phases sequentially (see plan §6 for edge case specifications):

### Phase A: Solution Discovery
- Find all `.sln` and `.csproj` files recursively.
- Parse project-to-project dependencies from `<ProjectReference>` tags.
- Traverse up directory tree for `Directory.Packages.props` (CPM) and `Directory.Build.props`.
- Resolve effective package versions accounting for CPM inheritance chain, including `VersionOverride` attribute priority.
- Map solution folder hierarchy from `.sln` file structure.

### Phase B: Entry Point & Extension Discovery
- Parse `Program.cs` / `Startup.cs` for DI registrations, middleware, host setup.
- **Scan ALL source files** (`*.cs`) for `public static IServiceCollection Add...` extension methods — extract full method body using brace-balancing parser.
- Detect `WebApplication.CreateBuilder()` vs `CreateDefaultBuilder()`.
- Identify controller/base class inheritance patterns (`[ApiController]`, `ControllerBase`).
- Discover all `IConsumer<T>` implementations for EDA inventory.

### Phase C: Namespace Architecture Analysis
- Extract namespace conventions from up to **2000** `.cs` files (increased from 500 for better coverage).
- Correlate namespaces with directory structure.
- Infer architectural boundaries from naming patterns (`*.Domain.*`, `*.Application.*`, etc.).
- **Fallback layer inference**: When namespace scanning is limited, infer layers from project names matching patterns like `*Infrastructure*`, `*API*`, `*Host*`, `*Persistence*`. This ensures at least partial layer classification even in large solutions where not all source files are scanned.
- Classify layers detected (Clean/Onion, Layered, Modular Monolith).

### Phase D: Pattern Detection
- Interface + implementation pairs (Repository pattern signal).
- Generic constraints analysis (Factory/Strategy signals).
- Abstract base classes and their consumers.
- MediatR `IRequestHandler<...>` implementations for CQRS detection.
- EF Core `DbContext` discovery — extract class signatures + `OnModelCreating` body.
- Attribute-based patterns (`[ApiController]`, `[Authorize]`, `[Fact]`, `[Test]`).

### Phase E: Test Structure & Code Style Analysis
- Find test projects by `.csproj` naming convention (`.Tests.csproj`, `*Tests.*`).
- Detect test framework from package references + attribute usage (`[Fact]` → xUnit, `[Test]` → NUnit/MSTest).
- Analyze mock library usage (Moq, NSubstitute, FakeItEasy) and data generation tools (Bogus/Faker.NET).
- **Arrange-Act-Assert detection**: Identify A-A-A pattern strength via comment markers (`// Act`, `// Assert`), section spacing between logical blocks, named variables (`result`, `expected`), Moq setup patterns (`.Setup().Returns()`), and FluentAssertions/Shouldly chains (`.Should().Be()`, `.ShouldNotBeNull()`). Report overall strength: strong/moderate/weak.
- **Test naming convention analysis**: Classify dominant test method naming style — e.g., `xunit_convention` (`MethodName_State_ExpectedResult` snake_case with PascalCase segments), `descriptive_sentence` (`it_should_do_this_when_that`), or `pascal_separated` (`MethodName_State_ExpectedResult`). Expanded heuristics detect C#-specific test indicators including `_when`, `_given`, `_and`, `_setup`, `_fixture`, `_specification`, `_scenario`, and action verbs like `creates`, `returns`, `throws`, `handles`, `processes`, `validates`.

### Phase H: Code Style & Convention Analysis
- **Class naming conventions**: Detect common suffixes/prefixes (DTO, Repository, Service, Handler, etc.) across all class declarations.
- **Inheritance hierarchies**: Build base→derived trees from class declarations; report top 15 hierarchies by derived count. Useful for understanding patterns like `BaseEntity → User/Customer`, `IArchitectureDetector → ApplicationArchitectureDetector/DataAccessPatternDetector`.
- **Namespace-location correlation**: Map namespace prefixes to file paths — reveals "where files live" rules (e.g., `Domain.Entities.*` always in `src/Domain/Entities/`).
- **Partial classes detection**: Count partial class usages (common with generated code or designer files).
- **Static utility classes**: Identify static-only classes that serve as extension methods holders or helper utilities.

### Phase F: External Dependencies Catalog
- Parse all `<PackageReference>` elements across solutions with CPM-aware version resolution.
- Group packages into semantic categories (logging, auth, mapping, caching, etc.).
- Report Central Package Management adoption status and inheritance chain.

### Phase G: Observability & Messaging Detection
- Scan for OpenTelemetry packages + `AddOpenTelemetry()` registration — trace/metrics/exporter targets.
- Detect ActivitySource declarations in source code (custom instrumentation count).
- Scan for MassTransit/Rebus/NServiceBus/Azure Service Bus/RabbitMQ package refs.
- Identify `IConsumer<T>` classes and message types for EDA consumer inventory.
- Detect outbox/inbox patterns (`EntityFrameworkOutbox`, transactional messaging code).
- Classify broker technology (RabbitMQ vs Azure Service Bus vs Kafka/SQS).

## Output Validation

After invocation, validate these outputs:

| Expected Output | Description | Validation Check |
| --------------- | ----------- | ---------------- |
| `extract_data.json` | Structured extraction data from all phases | Valid JSON, >10KB for non-trivial solutions |
| `ARCHITECTURE.md` | Final synthesized document (LLM mode) | File exists, >20 lines |
| `extraction_errors.log` | Warnings/errors per phase (if any) | Exists (may be empty in normal operation) |

If the script exits with code 0 but produces no output files or empty JSON, treat as a failure and report to user.

## Agent Synthesis Workflow (Workflow A)

When running in `--no-llm` mode (the default), **you** — the agent — must synthesize the final ARCHITECTURE.md from the structured extraction data. Follow this procedure:

### Critical: Prevent Context Window Truncation

For solutions with >10 projects or large DI registries, generating ARCHITECTURE.md in a single LLM call will exceed context window limits and produce truncated output. Use this chunked approach:

1. **Read `extract_data_compressed.json`** (preferred) — this is ~70% smaller than full JSON while preserving all architectural signals. Falls back to `extract_data.json` if compressed version doesn't exist.
2. **Read `references/output-template.md`** for the exact section structure and heading format.
3. **Generate ARCHITECTURE.md using 3 sequential temp files + concatenation** (see detailed procedure below).
4. **Report completion** with summary stats.

#### Recommended File Writing Procedure: Temp Files + Concatenation

> **Why not a single `write` or large `edit` call?** A single write/edit for 500+ line documents can be silently truncated at context boundaries, produce malformed markdown, or partially overwrite existing content. Using separate tool calls per chunk guarantees each section is written completely before proceeding.

```bash
# Step 1: Write Chunk 1 to a temp file (this creates ARCHITECTURE.md)
# → Use the 'write' tool to create <target>/ARCHITECTURE_chunk_1.md
#   containing Sections 1-7 with the # Architecture Documentation header.

# Step 2: Append Chunk 2 from a second temp file
# → Use the 'write' tool to create <target>/ARCHITECTURE_chunk_2.md
#   containing Sections 8-14 starting with --- separator.
# → Concatenate: cat chunk_1 >> ARCHITECTURE.md, then cat chunk_2 >> ARCHITECTURE.md

# Step 3: Append Chunk 3 from a third temp file
# → Use the 'write' tool to create <target>/ARCHITECTURE_chunk_3.md
#   containing Sections 15-22 + footer note.
# → Concatenate: cat chunk_3 >> ARCHITECTURE.md

# Step 4: Clean up and validate
cat "<target-dir>/ARCHITECTURE_chunk_[0-9]*.md" > "<target-dir>/ARCHITECTURE.md"
rm -f "<target-dir>"/ARCHITECTURE_chunk_*.md
wc -l "<target-dir>/ARCHITECTURE.md"          # Should be 400-700 lines for typical solutions
grep "^## " "<target-dir>/ARCHITECTURE.md"    # Verify all 22 section headings present
tail -3 "<target-dir>/ARCHITECTURE.md"        # Verify footer note is intact
```

**Chunk boundaries (aligned with template sections):**

| Chunk | Sections | Content Summary |
|-------|----------|----------------|
| **chunk 1** | 1–7 | Solution Overview, Dependency Graph, Architecture Layers, Design Patterns, DI Container Analysis, Middleware Pipeline, Data Access Layer |
| **chunk 2** | 8–14 | API Surface, Test Architecture, External Packages Catalog, Configuration System, Cross-Cutting Concerns, Health Checks & Monitoring, Background Services |
| **chunk 3** | 15–22 + footer | gRPC/Blazor, DDD Primitives Assessment, Observability & Telemetry, Event-Driven Architecture/Messaging, Package Management Strategy, Configuration & Environment Strategy, Limitations & Caveats, document footer |

> **Alternative approach — single `write` call:** If the solution has ≤10 projects and the total expected output is <300 lines (e.g., small solutions with few DbContexts/controllers), a single `write` tool call for all sections at once can work. Use judgment based on extraction data density before choosing this route.

> **Important: Section separator.** Each chunk file should start with `---\n` (markdown horizontal rule) as a section boundary, except Chunk 1 which starts directly with `# Architecture Documentation`. After concatenation, verify no duplicate `---` separators appear between chunks.

### Synthesis Prompt Template (per chunk)

When building each synthesis prompt for the LLM, use this structure:

```
You are an expert .NET architect documenting the architecture of a C# codebase.
The user has provided structured extraction data from automated static analysis.
Your task is to write SPECIFIC SECTIONS of ARCHITECTURE.md documentation.

=== SECTIONS TO WRITE ===
{only_sections_1_to_7_or_8_to_14_or_15_to_22_from_template}

=== EXTRACTED DATA FOR THESE SECTIONS ===
{relevant_data_for_these_sections_only}

Rules:
- Write ONLY the sections listed above. Do NOT add any other sections.
- Use EXACTLY the section numbering and headings shown in the template.
- Fill every {{placeholder}} using the extracted data provided below.
- If data for a section is empty/unknown, write "Not detected / not applicable" rather than inventing content.
- For DDD Primitives Assessment (Section 17), evaluate entity class signatures semantically — report as Rich Domain, Anemic Model, or Mixed.
- Be concise but thorough. Never repeat information across sections.
- Use markdown tables where the template shows table structures.
- CRITICAL: Never include YAML frontmatter (`--- ... ---`) or any header instructions/metadata comments in the output. The document should start directly with `# Architecture Documentation` and end at the last section's footer note.

**Rules:**
- Fill in every `{{placeholder}}` using the extracted data.
- If data is empty or unknown, write "Not detected / not applicable" rather than inventing content.
- For DDD Primitives Assessment (Section 17), evaluate entity class signatures semantically — consider whether entities contain behavioral methods with business logic vs pure data classes. Report as Rich Domain, Anemic Model, or Mixed.
- Use markdown tables where the template shows table structures.
- Do NOT add sections beyond those defined in the template.
- **CRITICAL: Never include YAML frontmatter (`--- ... ---`) or any header instructions/metadata comments in the output.** The document should start directly with `# Architecture Documentation` and end at the last section's footer note. No `<!-- -->`, no `---` separators at the top, no "This is a generated file" disclaimers unless explicitly part of the template content.

## Output Artifacts Location

All outputs go to `<target-dir>` by default:
- **`ARCHITECTURE.md`** — Final architecture documentation (synthesized, human-readable). Sections include: Solution Overview, Project Structure, Dependency Graph, Architecture Layers, Design Patterns, DI Container Analysis, Middleware Pipeline, Data Access Layer, API Surface, Test Architecture, External Packages, Configuration System, Cross-Cutting Concerns, Health Checks & Monitoring, Background Services, API Versioning, gRPC Services, Blazor Architecture, DDD Primitives Assessment, Observability & Telemetry, Event-Driven Architecture/Messaging, Package Management Strategy.
- **`extract_data.json`** — Raw structured extraction data from all phases (JSON object with keys matching each phase name). Used for debugging and can be fed into the LLM prompt directly.
- **`extraction_errors.log`** — Per-phase warnings and errors. Empty in normal operation; contains details on parse failures, unresolved references, or skipped sections.

## Edge Case Handling (Encoded in Script)

The script implements these edge case specifications automatically:

1. **CPM Version Override Resolution**: Checks `VersionOverride` attribute first before falling back to `Directory.Packages.props`. Traverses up directory tree for CPM files.
2. **Solution Dependency Resolution via Disk Scan**: Primary source is disk scan of `<ProjectReference>` tags across all `.csproj` files. Falls back to `.sln` GUID matching only if disk scan finds zero references.
3. **Brace-Balanced Method Body Extraction**: Uses a brace-counting parser (not regex) to capture full method bodies for DI extension methods, handling nested braces from lambdas and control flow blocks.
4. **LLM Context Token Budget Limits**: Enforces strict line caps per section when preparing data for LLM synthesis: DI max 150 lines, middleware max 80 lines, DbContext per context max 60 lines, mapper config max 50 lines, entity signatures capped at `--entity-samples`.

## Limitations & Caveats

Record these in the generated document's "Limitations" section:

- **Regex-based extraction for MVP**: The script uses pattern matching and brace-balancing parsers rather than Roslyn semantic analysis. It covers ~95% of detection signals but may miss edge cases like dynamically constructed service registrations (e.g., `.Add(typeof(MyAssembly).GetTypes().Where(t => t.Name.EndsWith("Service")).ToList())`).
- **No runtime behavior inference**: Static analysis cannot determine actual dependency resolution order or runtime DI container configuration beyond registration declarations.
- **Namespace convention assumptions**: Layer classification from namespace patterns is heuristic — not all projects follow `*.Domain.*` / `*.Application.*` conventions even when architecturally separated.
- **LLM synthesis quality depends on model capability**: The final prose section relies on the LLM's ability to synthesize structured data into coherent documentation. Use a capable model for best results.
- **Large solutions may exceed token budgets**: Even with caps, very large codebases (50+ DbContexts, 200+ DI registrations) will produce dense extraction data. Consider increasing `--token-budget-*` flags or running in `--no-llm` mode and reviewing raw JSON.

## Best Practices

1. Always run `project-discovery` first to confirm C#/.NET presence and get baseline metrics — but this skill can operate standalone if the target is known.
2. Never include API keys or credentials in generated documents or logs.
3. Run architecture extraction as part of CI/CD for monoliths undergoing refactoring — it provides a before-state snapshot for comparison after architectural changes.
4. After generation, review the ARCHITECTURE.md for accuracy against actual codebase structure; the LLM synthesis phase may occasionally misinterpret patterns.
5. If the Python script fails entirely (e.g., due to unusual solution structure), fall back to manual documentation using the output-template.md as a guide.
6. For multi-repository microservice setups: run this skill per-service and combine results at the top level with inter-service dependency notes.
7. **Use temp-file concatenation for large documents:** Never attempt a single `write` or `edit` call for >300-line ARCHITECTURE.md files. Always use separate tool calls per chunk written to temp `.md` files, then concatenate via bash `cat`. This prevents silent truncation at context boundaries that corrupts markdown structure and produces duplicate sections.
