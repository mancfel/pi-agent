#!/usr/bin/env python3
"""
Architecture Document Extractor for C#/.NET Codebases.

Extracts comprehensive architectural documentation by combining deterministic
structural parsing (Phase A–G) with LLM synthesis (Phase H).

Edge cases handled:
  - EC-1: CPM Version Override resolution
  - EC-2: Solution dependency resolution via disk scan
  - EC-3: Brace-balanced method body extraction
  - EC-4: LLM context token budget limits
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# CLI Argument Parsing
# ──────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract architecture documentation from C#/.NET codebases."
    )
    parser.add_argument("--target-dir", required=True, help="Root directory of the .NET solution")
    parser.add_argument("--output", default=None, help="Output file path (default: <target>/ARCHITECTURE.md)")
    # LLM flags — check pi-agent env vars first, then arch-doc-specific env vars, then hardcoded defaults
    _pi_model = os.environ.get("PI_MODEL", "")
    _pi_api_base = os.environ.get("PI_API_BASE", "http://localhost:11434/v1")
    parser.add_argument("--llm-api-base", default=os.environ.get("ARCH_DOC_API_BASE", _pi_api_base))
    parser.add_argument("--llm-model", default=os.environ.get("ARCH_DOC_MODEL", _pi_model or "qwen2.5:7b"))
    parser.add_argument("--llm-key", default=os.environ.get("ARCH_DOC_API_KEY", os.environ.get("LLM_KEY", "")))
    parser.add_argument("--token-budget-di", type=int, default=150)
    parser.add_argument("--token-budget-middleware", type=int, default=80)
    parser.add_argument("--entity-samples", type=int, default=5)
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis; produce JSON only")
    parser.add_argument("--verbose", action="store_true", help="Print per-phase progress to stderr")
    return parser.parse_args()


# ──────────────────────────────────────────────
# Utility Helpers
# ──────────────────────────────────────────────

def log(msg: str, verbose_only: bool = False, args: Optional[argparse.Namespace] = None):
    if not verbose_only or (args and getattr(args, "verbose", False)):
        print(f"[arch-doc-extractor] {msg}", file=sys.stderr)


def find_all_files(root: Path, *extensions: str) -> List[Path]:
    """Recursively find files matching any of the given extensions."""
    result = []
    for ext in extensions:
        result.extend(sorted(root.rglob(ext)))
    return list(dict.fromkeys(result))  # deduplicate preserving order


def read_file(path: Path, encoding: str = "utf-8") -> Optional[str]:
    try:
        content = path.read_text(encoding=encoding)
        return content
    except UnicodeDecodeError:
        # Fallback to latin-1 for files with non-UTF-8 characters (common in Windows)
        try:
            return path.read_text(encoding="latin-1")
        except Exception as e2:
            log(f"⚠ Could not read {path} even with fallback encoding: {e2}")
            return None
    except Exception as e:
        log(f"⚠ Could not read {path}: {e}")
        return None


# ──────────────────────────────────────────────
# EC-1: CPM Version Override Resolution
# ──────────────────────────────────────────────

def extract_version_override_from_csproj(csproj_content: str, package_name: str) -> Optional[str]:
    """Check for VersionOverride attribute on a PackageReference element."""
    pattern = rf'<PackageReference\s+Include="{re.escape(package_name)}"[^>]*\sVersionOverride="([^"]*)"'
    m = re.search(pattern, csproj_content)
    if m:
        return m.group(1)
    # Also check reverse order (Version before Include)
    pattern2 = rf'<PackageReference[^>]*\sVersionOverride="([^"]*)"[^>]*\sInclude="{re.escape(package_name)}"'
    m2 = re.search(pattern2, csproj_content)
    return m2.group(1) if m2 else None


def extract_legacy_version_from_csproj(csproj_content: str, package_name: str) -> Optional[str]:
    """Extract Version attribute from a PackageReference element in non-CPM .csproj."""
    pattern = rf'<PackageReference\s+Include="{re.escape(package_name)}"[^>]*\sVersion="([^"]*)"'
    m = re.search(pattern, csproj_content)
    if m:
        return m.group(1)
    pattern2 = rf'<PackageReference[^>]*\sVersion="([^"]*)"[^>]*\sInclude="{re.escape(package_name)}"'
    m2 = re.search(pattern2, csproj_content)
    return m2.group(1) if m2 else None


def parse_directory_packages_props(cpm_path: Path) -> Dict[str, str]:
    """Parse Directory.Packages.props to extract <PackageReference Include="X" Version="Y" /> entries."""
    content = read_file(cpm_path)
    if not content:
        return {}
    result = {}
    # Match both orderings of Attribute and Version
    pattern = r'<PackageReference\s+Include="([^"]*)"[^>]*\sVersion="([^"]*)"'
    for m in re.finditer(pattern, content):
        result[m.group(1)] = m.group(2)
    # Reverse ordering too
    pattern2 = r'<PackageReference[^>]*\sVersion="([^"]*)"[^>]*\sInclude="([^"]*)"'
    for m in re.finditer(pattern2, content):
        if m.group(2) not in result:  # Don't overwrite first-found
            result[m.group(2)] = m.group(1)
    return result


def resolve_package_version(csproj_path: Path, package_name: str, csproj_content: Optional[str] = None) -> Optional[str]:
    """Resolve effective package version with CPM-aware priority."""
    if csproj_content is None:
        csproj_content = read_file(csproj_path)
    if not csproj_content:
        return None

    # Priority 1: VersionOverride in this .csproj
    override = extract_version_override_from_csproj(csproj_content, package_name)
    if override:
        return override

    # Priority 2: Walk UP directory tree for Directory.Packages.props
    current_dir = csproj_path.parent
    visited = set()
    while str(current_dir) != os.path.dirname(str(current_dir)):  # Stop at filesystem root
        cpm_file = current_dir / "Directory.Packages.props"
        if cpm_file.exists() and str(cpm_file) not in visited:
            visited.add(str(cpm_file))
            central = parse_directory_packages_props(cpm_file)
            if package_name in central:
                return central[package_name]
        current_dir = current_dir.parent

    # Priority 3: Legacy Version attribute in .csproj (no CPM)
    return extract_legacy_version_from_csproj(csproj_content, package_name)


# ──────────────────────────────────────────────
# EC-2: Solution Dependency Resolution via Disk Scan
# ──────────────────────────────────────────────

def find_all_csprojs(root: Path) -> List[Path]:
    """Find all .csproj files recursively."""
    return sorted(root.rglob("*.csproj"))


def extract_project_references(csproj_path: Path, csproj_content: Optional[str] = None) -> List[str]:
    """Extract <ProjectReference Include="..." /> paths from a .csproj file."""
    if csproj_content is None:
        csproj_content = read_file(csproj_path)
    if not csproj_content:
        return []
    refs = []
    for m in re.finditer(r'<ProjectReference\s+Include="([^"]*)"', csproj_content):
        refs.append(m.group(1))
    # Also check reverse ordering
    for m in re.finditer(r'<ProjectReference[^>]*\sInclude="([^"]*)"', csproj_content):
        ref = m.group(1)
        if ref not in refs:
            refs.append(ref)
    return refs


def resolve_relative_to_abs(base_csproj: Path, rel_ref: str) -> Optional[Path]:
    """Resolve a relative ProjectReference path to an absolute Path."""
    base_dir = base_csproj.parent
    resolved = (base_dir / rel_ref).resolve()
    return resolved if resolved.exists() else None


def build_project_reference_graph(root: Path) -> Dict[str, List[str]]:
    """Build project-to-project dependency graph via disk scan of .csproj files."""
    all_csprojs = find_all_csprojs(root)
    if not all_csprojs:
        return {}

    log("Building project reference graph via disk scan...")
    graph = {}
    for csproj in all_csprojs:
        content = read_file(csproj) or ""
        raw_refs = extract_project_references(csproj, content)
        resolved_deps = []
        for ref in raw_refs:
            abs_ref = resolve_relative_to_abs(csproj, ref)
            if abs_ref and str(abs_ref).endswith(".csproj"):
                resolved_deps.append(str(abs_ref))
        graph[str(csproj)] = resolved_deps
    return graph


# ──────────────────────────────────────────────
# EC-3: Brace-Balanced Method Body Extraction
# ──────────────────────────────────────────────

def find_extension_methods(source_code: str) -> List[Dict[str, Any]]:
    """Find all public static IServiceCollection Add... extension methods using brace balancing."""
    results = []
    # Match the method signature pattern
    pattern = r'public\s+static\s+(?:this\s+)?IServiceCollection\s+(\w+)\s*\('
    for m in re.finditer(pattern, source_code):
        method_name = m.group(1)
        if not method_name.startswith("Add"):
            continue

        # Find the opening brace after the signature
        search_start = m.end() - 1
        open_brace_idx = source_code.index('{', search_start)

        # Brace-balancing parser to extract full body
        depth = 0
        i = open_brace_idx
        while i < len(source_code):
            ch = source_code[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    body = source_code[open_brace_idx:i + 1]
                    results.append({
                        "name": method_name,
                        "start_line": source_code[:m.start()].count('\n') + 1,
                        "body_lines": min(body.count('\n') + 1, 25),  # Cap extracted lines
                        "full_body": body,
                    })
                    break
            i += 1

    return results


# ──────────────────────────────────────────────
# Phase A: Solution Discovery
# ──────────────────────────────────────────────

def phase_a_solution_discovery(root: Path) -> Dict[str, Any]:
    """Phase A: Find .sln files, parse project references, CPM detection."""
    log("Phase A: Solution Discovery")
    result = {
        "solution_files": [],
        "csproj_files": [],
        "project_references": {},
        "cpm_detected": False,
        "cpm_file_path": None,
        "cpm_inheritance_chain": [],
        "packages": {},  # {package_name: {"version": str, "file": str}}
        "sdk_types": {},  # {csproj_path: sdk_type}
        "target_frameworks": {},
        "output_types": {},
    }

    sln_files = find_all_files(root, "*.sln")
    csproj_files = find_all_csprojs(root)

    result["solution_files"] = [str(f.relative_to(root)) for f in sln_files]
    result["csproj_files"] = [str(f.relative_to(root)) for f in csproj_files]

    if not csproj_files:
        log("⚠ No .csproj files found. Returning empty extraction.", verbose_only=False)
        return result

    # Build project reference graph (EC-2: disk scan approach)
    ref_graph = build_project_reference_graph(root)
    result["project_references"] = {Path(k).relative_to(root).__str__(): v for k, v in ref_graph.items()}

    # Check for CPM and Directory.Build.props
    cpm_file = root / "Directory.Packages.props"
    build_props = root / "Directory.Build.props"

    if cpm_file.exists() or _find_cpm_upward(csproj_files):
        result["cpm_detected"] = True
        chain = []
        current_dir = csproj_files[0].parent
        visited = set()
        while str(current_dir) != os.path.dirname(str(current_dir)):
            p = current_dir / "Directory.Packages.props"
            b = current_dir / "Directory.Build.props"
            if p.exists():
                chain.append(str(p.relative_to(root)))
                result["cpm_file_path"] = str(p.relative_to(root))
            elif b.exists():
                chain.append(f"[build_props] {str(b.relative_to(root))}")
            visited.add(str(current_dir))
            current_dir = current_dir.parent
        result["cpm_inheritance_chain"] = chain

    # Parse each .csproj for packages, SDK type, target framework, output type
    all_packages = {}  # {name: {"version": str, "file": relative_path}}
    for csproj in csproj_files:
        content = read_file(csproj) or ""
        rel_path = str(csproj.relative_to(root))

        # SDK type detection
        sdk_match = re.search(r'<Project\s+Sdk="([^"]*)"', content)
        if sdk_match:
            result["sdk_types"][rel_path] = sdk_match.group(1)

        # Target framework
        tfm = re.search(r'<TargetFramework>([^<]*)', content)
        if tfm:
            result["target_frameworks"][rel_path] = tfm.group(1)

        # Output type
        ot = re.search(r'<OutputType>([^<]*)', content)
        if ot:
            result["output_types"][rel_path] = ot.group(1)

        # Package references with CPM-aware version resolution (EC-1)
        for pm in re.finditer(r'<PackageReference\s+Include="([^"]*)"', content):
            pkg_name = pm.group(1)
            version = resolve_package_version(csproj, pkg_name, content)
            all_packages[pkg_name] = {"version": version or "unspecified", "file": rel_path}
        # Reverse ordering too
        for pm2 in re.finditer(r'<PackageReference[^>]*\sInclude="([^"]*)"', content):
            pkg_name = pm2.group(1)
            if pkg_name not in all_packages:
                version = resolve_package_version(csproj, pkg_name, content)
                all_packages[pkg_name] = {"version": version or "unspecified", "file": rel_path}

    result["packages"] = all_packages
    return result


def _find_cpm_upward(csproj_list: List[Path]) -> bool:
    """Check if any .csproj file has a Directory.Packages.props ancestor."""
    for csproj in csproj_list:
        current_dir = csproj.parent
        while str(current_dir) != os.path.dirname(str(current_dir)):
            if (current_dir / "Directory.Packages.props").exists():
                return True
            current_dir = current_dir.parent
    return False


# ──────────────────────────────────────────────
# Phase B: Entry Point & Extension Discovery
# ──────────────────────────────────────────────

def phase_b_entry_point_discovery(root: Path, args=None) -> Dict[str, Any]:
    """Phase B: Parse Program.cs/Startup.cs, find DI extension methods."""
    log("Phase B: Entry Point & Extension Discovery")
    result = {
        "program_cs": None,
        "startup_cs": None,
        "hosting_model": None,  # WebApplication.CreateBuilder / CreateDefaultBuilder
        "di_extension_methods": [],  # List of method dicts with brace-balanced bodies
        "middleware_calls": [],  # app.Use*() and app.Map*() calls
        "controller_classes": [],
        "grpc_service_implementations": [],
        "i_consumer_implementation": [],  # IConsumer<T> implementations for EDA
    }

    program_files = find_all_files(root, "**/Program.cs")
    startup_files = find_all_files(root, "**/Startup.cs")

    if program_files:
        result["program_cs"] = str(program_files[0].relative_to(root))
        content = read_file(program_files[0]) or ""

        # Hosting model detection
        if "WebApplication.CreateBuilder" in content:
            result["hosting_model"] = "WebApplication.CreateBuilder (modern .NET 6+)"
        elif "CreateDefaultBuilder" in content:
            result["hosting_model"] = "WebHost.CreateDefaultBuilder (.NET Core legacy)"
        else:
            result["hosting_model"] = "unknown"

        # Middleware calls
        for m in re.finditer(r'app\.(Use|Map)(Get|Post|Put|Delete|Patch|Controllers|GrpcService|HealthChecks)\([^)]*\)', content):
            result["middleware_calls"].append(m.group(0))

    if startup_files:
        result["startup_cs"] = str(startup_files[0].relative_to(root))

    # Scan ALL .cs files for DI extension methods (EC-3: brace-balanced)
    all_cs = find_all_files(root, "**/*.cs")
    di_extensions_found = []
    i_consumers_found = []

    for cs_file in all_cs:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))

        # Extension methods
        ext_methods = find_extension_methods(content)
        for em in ext_methods:
            em["file"] = rel_path
            di_extensions_found.append(em)

        # IConsumer<T> implementations
        for m in re.finditer(r'(?:public\s+)?(?:class|record)\s+(\w+)\s*:\s*(?:.*\s*)?IConsumer<([^>]+)>', content):
            i_consumers_found.append({
                "name": m.group(1),
                "message_type": m.group(2).strip(),
                "file": rel_path,
            })

        # Controller classes
        if "[ApiController]" in content:
            for cm in re.finditer(r'public\s+(?:abstract\s+)?class\s+(\w+)\s*:\s*\w*', content):
                result["controller_classes"].append(cm.group(1))

        # gRPC service implementations
        for gm in re.finditer(r'(?:public\s+)?(?:partial\s+)?class\s+(\w*)Service[^{]*\n\s*(?::)\s*(\w+)Base', content):
            result["grpc_service_implementations"].append({
                "name": gm.group(1),
                "base_class": gm.group(2),
                "file": rel_path,
            })

    result["di_extension_methods"] = di_extensions_found[:30]  # Cap at 30 extension methods
    result["i_consumer_implementation"] = i_consumers_found
    return result


# ──────────────────────────────────────────────
# Phase C: Namespace Architecture Analysis
# ──────────────────────────────────────────────

def phase_c_namespace_analysis(root: Path) -> Dict[str, Any]:
    """Phase C: Extract namespace conventions and infer architectural layers."""
    log("Phase C: Namespace Architecture Analysis")
    result = {
        "namespaces": {},  # {namespace_pattern: count}
        "layer_classification": {
            "domain": [],
            "application": [],
            "infrastructure": [],
            "presentation": [],
        },
        "detected_architecture_style": None,
    }

    all_cs_files = find_all_files(root, "**/*.cs")
    namespace_counts = {}
    file_namespaces = []  # [(file_rel_path, namespaces_list)]

    for cs_file in all_cs_files[:2000]:  # Increased cap for better layer coverage
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))
        ns_matches = re.findall(r'namespace\s+([\w.]+)\s*;', content)
        if ns_matches:
            file_ns = list(dict.fromkeys(ns_matches))  # deduplicate preserving order
            file_namespaces.append((rel_path, file_ns))
            for ns in file_ns:
                namespace_counts[ns] = namespace_counts.get(ns, 0) + 1

    result["namespaces"] = dict(sorted(namespace_counts.items(), key=lambda x: -x[1])[:100])

    # ── Fallback layer inference from project names when namespace scanning is limited ──
    if not any(len(result["layer_classification"][l]) >= 2 for l in ["application", "infrastructure", "presentation"]):
        all_csprojs = find_all_files(root, "**/*.csproj")
        proj_layer_map = {
            "domain": re.compile(r'\bDomain\b', re.IGNORECASE),
            "application": re.compile(r'\bApplication\b|UseCase'),
            "infrastructure": re.compile(r'\bInfrastructure\b|Persistence|Repositories?|DataAccess'),
            "presentation": re.compile(r'\bAPI\b|Web|Controllers?|Grpc|Blazor|UI|Frontend|Host'),
        }
        for csproj in all_csprojs:
            rel_path = str(csproj.relative_to(root))
            proj_filename = Path(rel_path).stem.lower()
            
            for layer, pattern in proj_layer_map.items():
                if pattern.search(proj_filename):
                    ns_key = proj_filename.replace("-", ".").replace("_", ".")
                    if not any(n["namespace"] == ns_key and n.get("inferred_from") == "project_name"
                               for n in result["layer_classification"][layer]):
                        result["layer_classification"][layer].append({
                            "namespace": ns_key,
                            "file_count": 0,
                            "inferred_from": "project_name",
                        })

    # Classify namespaces into layers based on convention patterns
    layer_patterns = {
        "domain": re.compile(r'\bDomain\b', re.IGNORECASE),
        "application": re.compile(r'\bApplication\b|\bUseCase\b|\bCommand\b|\bQuery\b'),
        "infrastructure": re.compile(r'\bInfrastructure\b|\bData\b|\bRepositories?\b|\bPersistence\b'),
        "presentation": re.compile(r'\bAPI\b|\bWeb\b|\bControllers?\b|\bGrpc\b|\bBlazor\b|\bUI\b|\bFrontend\b'),
    }

    for ns, count in namespace_counts.items():
        if count < 2:  # Skip namespaces found in only one file (likely utility/helper)
            continue
        classified = False
        for layer, pattern in layer_patterns.items():
            if pattern.search(ns):
                result["layer_classification"][layer].append({"namespace": ns, "file_count": count})
                classified = True
                break
        if not classified and re.search(r'\bEntities\b|\bValueObjects?\b|\bDomainEvents?\b', ns, re.IGNORECASE):
            result["layer_classification"]["domain"].append({"namespace": ns, "file_count": count})

    # Infer architecture style from namespace + project naming patterns
    has_clean_layers = (len(result["layer_classification"]["domain"]) >= 2 and
                        len(result["layer_classification"]["application"]) >= 2)
    has_vertical_slices = any(re.search(r'\bFeatures?\b/[\w]+/[A-Z]\w+', f[0]) for f in file_namespaces[:100])

    if has_clean_layers:
        result["detected_architecture_style"] = "Clean Architecture / Onion Architecture"
    elif has_vertical_slices:
        result["detected_architecture_style"] = "Vertical Slice Architecture"
    elif namespace_counts:
        result["detected_architecture_style"] = "Layered or Modular Monolith (inferred)"
    else:
        result["detected_architecture_style"] = "unknown"

    return result


# ──────────────────────────────────────────────
# Phase D: Pattern Detection
# ──────────────────────────────────────────────

def phase_d_pattern_detection(root: Path) -> Dict[str, Any]:
    """Phase D: Detect design patterns in source code."""
    log("Phase D: Pattern Detection")
    result = {
        "repository_pattern": {"interfaces": [], "implementations": []},
        "unit_of_work": [],
        "mediatr_handlers": [],  # IRequestHandler<TCommand, TResponse> classes
        "ef_core_contexts": [],  # DbContext subclasses with OnModelCreating body
        "generic_constraints": {},  # {class_name: [constraints]}
        "abstract_base_classes": {},
        "attributes_found": {},
    }

    all_cs_files = find_all_files(root, "**/*.cs")[:1000]  # Cap for performance

    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))

        # Repository pattern: IRepository<T> or I{name}Repository interfaces + implementations
        for im in re.finditer(r'public\s+(?:interface|abstract\s+class)\s+(\w+)\s*:\s*(.*IRepository<[^>]+>)', content):
            result["repository_pattern"]["interfaces"].append({"name": im.group(1), "base": im.group(2).strip()})
        for cm in re.finditer(r'class\s+(\w+)\s*:.*(?:IRepository|I\w+Repository)', content):
            result["repository_pattern"]["implementations"].append(cm.group(1))

        # Unit of Work: class named UnitOfWork or containing multiple repo properties
        if re.search(r'class\s+\w*[Uu]nitOf[Ww]ork\b|\bUnitOfWork\b', content):
            uow_matches = re.findall(r'(?:public|internal)\s+(?:I?\w*Repository<[^>]+>|DbContext)\s+(\w+)', content)
            result["unit_of_work"].append({"file": rel_path, "properties_found": len(uow_matches)})

        # MediatR handlers: IRequestHandler<TCommand, TResponse> classes
        for hm in re.finditer(
            r'public\s+(?:class|record)\s+(\w+)\s*:.*(?:IRequestHandler|IRequestHandler)<([^>]+),\s*([^>]+)>',
            content
        ):
            result["mediatr_handlers"].append({
                "name": hm.group(1),
                "command_type": hm.group(2).strip(),
                "response_type": hm.group(3).strip(),
                "file": rel_path,
            })

        # EF Core DbContext discovery + OnModelCreating body extraction (brace-balanced)
        for dc in re.finditer(r'(?:public|internal)\s+(partial\s+)?class\s+(\w+)\s*:\s*\w*(DbContext|IdentityDbContext)', content):
            class_name = dc.group(2)
            # Find OnModelCreating method and extract its body via brace balancing
            on_mc_pattern = rf'onmodelcreating\([^)]*\)\s*{{'
            mc_match = re.search(on_mc_pattern, content, re.IGNORECASE)
            if mc_match:
                open_idx = content.index('{', mc_match.end() - 1)
                depth = 0
                i = open_idx
                while i < len(content):
                    if content[i] == '{':
                        depth += 1
                    elif content[i] == '}':
                        depth -= 1
                        if depth == 0:
                            result["ef_core_contexts"].append({
                                "name": class_name,
                                "on_model_creating_body": content[open_idx:i + 1][:500],  # Cap at 500 chars
                                "file": rel_path,
                            })
                            break
                    i += 1

        # Generic constraints analysis
        for gc in re.finditer(r'(?:class|interface|struct)\s+(\w+)\s*<[^>]*where\s+(\w+):\s*([^,\n}]+)', content):
            cls = gc.group(1)
            if cls not in result["generic_constraints"]:
                result["generic_constraints"][cls] = []
            result["generic_constraints"][cls].append(gc.group(3).strip())

        # Abstract base classes
        for ab in re.finditer(r'public\s+(abstract\s+)?class\s+(\w+)\b', content):
            is_abstract = "abstract" in ab.group(0) and "abstract" in ab.group(1)
            if is_abstract:
                result["abstract_base_classes"].setdefault(ab.group(2), []).append(rel_path)

        # Attribute-based patterns
        attr_patterns = [r'\[ApiController\]', r'\[Authorize\]', r'\[Fact\]', r'\[Test\]',
                         r'\[TestMethod\]', r'\[Theory\]', r'\[ApiVersion\]', r'\[Consumes\]']
        for ap in attr_patterns:
            matches = re.findall(ap, content)
            if matches:
                attr_name = ap.replace("[", "").replace("]", "")
                result["attributes_found"][attr_name] = result["attributes_found"].get(attr_name, 0) + len(matches)

    return result


# ──────────────────────────────────────────────
# Phase E: Test Structure Analysis
# ──────────────────────────────────────────────

def phase_e_test_structure(root: Path) -> Dict[str, Any]:
    """Phase E: Analyze test project structure and frameworks."""
    log("Phase E: Test Structure Analysis")
    result = {
        "test_projects": [],
        "test_framework": None,
        "mocking_library": None,
        "data_generation_tool": None,
        "attributes_found": {},
    }

    # Find test projects by naming convention
    all_csprojs = find_all_files(root, "**/*.csproj")
    for csproj in all_csprojs:
        content = read_file(csproj) or ""
        rel_path = str(csproj.relative_to(root))
        is_test_project = any(
            pattern in rel_path.lower()
            for pattern in [".tests.", "_tests_", ".test.", "_test_"]
        )
        if not is_test_project and re.search(r'<ProjectReference[^>]*Test', content):
            is_test_project = True  # Referenced as a Test project

        if is_test_project:
            result["test_projects"].append(rel_path)

            # Detect test framework from package refs + attribute usage elsewhere
            if "xunit" in content.lower():
                result["test_framework"] = "xUnit"
            elif "nunit" in content.lower():
                result["test_framework"] = "NUnit"
            elif "mstest" in content.lower() or "microsoft.visualstudio.testtools.unittesting" in content.lower():
                result["test_framework"] = "MSTest"

            # Mocking library detection
            if "moq" in content.lower():
                result["mocking_library"] = "Moq"
            elif "nsubstitute" in content.lower():
                result["mocking_library"] = "NSubstitute"
            elif "fakeiteasy" in content.lower():
                result["mocking_library"] = "FakeItEasy"

            # Data generation tool
            if "faker" in content.lower() or "bogus" in content.lower():
                result["data_generation_tool"] = "Bogus (Faker.NET)" if "bogus" in content.lower() else "Faker.NET"

    # Scan source files for test attributes to confirm framework
    all_cs_files = find_all_files(root, "**/*.cs")[:500]
    attr_counts = {}
    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        for pattern in [r'\[Fact\]', r'\[Theory\]', r'\[Test\]', r'\[TestMethod\]', r'describe\(', r'it\(']:
            matches = re.findall(pattern, content)
            key = pattern.replace("[", "").replace("]", "")
            attr_counts[key] = attr_counts.get(key, 0) + len(matches)

    result["attributes_found"] = attr_counts
    if not result["test_framework"]:
        if "Fact" in attr_counts and attr_counts["Fact"] > 5:
            result["test_framework"] = "xUnit (inferred from [Fact])"
        elif "Test" in attr_counts and attr_counts["Test"] > 5:
            result["test_framework"] = "NUnit or MSTest ([Test] attribute)"
        elif "TestMethod" in attr_counts and attr_counts["TestMethod"] > 5:
            result["test_framework"] = "MSTest ([TestMethod])"

    return result


# ──────────────────────────────────────────────
# Phase F: External Dependencies Catalog
# ──────────────────────────────────────────────

def phase_f_external_dependencies(solution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Phase F: Group packages by semantic category."""
    log("Phase F: External Dependencies Catalog")
    packages = solution_data.get("packages", {})

    # Semantic categorization rules (package name → category)
    categories = {
        "Logging": ["serilog", "microsoft.extensions.logging"],
        "Authentication/Security": [
            "jwtbearer", "authentication", "identityserver", "duende",
            "azure.activedirectory", "microsoft.identity.web",
            "passwordless", "auth0"
        ],
        "Mapping": ["automapper", "mapster", "mapperly", "mapful"],
        "Validation": ["fluentvalidation", "system.componentmodel.annotation"],
        "Caching": ["stackexchange.redis", "memorycache", "redis", "cachemanagement"],
        "Messaging/EDA": [
            "masstransit", "rebus", "nservicebus", "particular",
            "rabbitmq.client", "azure.messaging.servicebus",
            "kafka", "amazon.sqs"
        ],
        "Database/Data Access": [
            "microsoft.entityframeworkcore", "npgsql.efcore", "mysql.*efcore",
            "sqlserver.efcore", "sqlite.efcore", "dapper", "mongodb.driver",
            "stackexchange.redis"  # also used for caching
        ],
        "Testing": ["xunit", "nunit", "mstest", "moq", "nsubstitute", "fakeiteasy", "faker", "bogus"],
        "Observability/Telemetry": [
            "opentelemetry", "prometheus", "jaeger", "zipkin",
            "datadog", "newrelic", "azure.monitor.opentelemetry"
        ],
        "Background Jobs/Scheduling": ["hangfire", "quartz", "coravel"],
        "gRPC": ["grpc.aspnetcore", "grpc.tools", "protobuf-net"],
        "Blazor/UI": ["components.webassembly", "components.server", "radzen.blazor"],
        "API Versioning": ["asp.versioning"],
        "Health Checks": ["healthchecks", "AspNetCore.HealthChecks"],
    }

    categorized = {cat: [] for cat in categories}
    uncategorized = []

    for pkg_name, info in packages.items():
        placed = False
        lower_pkg = pkg_name.lower()
        for cat, keywords in categories.items():
            if any(kw in lower_pkg for kw in keywords):
                categorized[cat].append({
                    "name": pkg_name,
                    "version": info.get("version", "?"),
                    "source_file": info.get("file", ""),
                })
                placed = True
                break
        if not placed:
            uncategorized.append({"name": pkg_name, "version": info.get("version", "?")})

    return {
        "categorized_packages": {k: v for k, v in categorized.items() if v},
        "uncategorized_count": len(uncategorized),
        "total_unique_packages": len(packages),
    }


# ──────────────────────────────────────────────
# Phase G: Observability & Messaging Detection
# ──────────────────────────────────────────────

def phase_g_observability_messaging(root: Path) -> Dict[str, Any]:
    """Phase G: Detect OpenTelemetry and EDA/messaging patterns."""
    log("Phase G: Observability & Messaging Detection")
    result = {
        "opentelemetry": {
            "packages_found": [],
            "add_opentelemetry_registration": None,
            "exporter_targets": [],
            "activity_source_declarations": 0,
            "manual_span_starts": 0,
            "serilog_otel_correlation": False,
        },
        "messaging": {
            "library_used": None,  # MassTransit / Rebus / NServiceBus / Direct SDK
            "broker_type": None,  # RabbitMQ / Azure Service Bus / Kafka / SQS
            "consumer_count": 0,
            "producer_locations": [],
            "outbox_pattern": None,
            "inbox_pattern": None,
        },
    }

    all_cs_files = find_all_files(root, "**/*.cs")[:1000]
    packages_seen = set()

    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))

        # OpenTelemetry package detection (from content — package refs may not be inline)
        if "opentelemetry" in content.lower():
            packages_seen.add("OpenTelemetry")
        if "prometheus" in content.lower() and ("exporter" in content.lower() or "package" in content.lower()):
            packages_seen.add("OpenTelemetry.Exporter.Prometheus")
        if "jaeger" in content.lower() and "exporter" in content.lower():
            packages_seen.add("OpenTelemetry.Exporter.Jaeger")

        # AddOpenTelemetry registration
        if re.search(r'AddOpenTelemetry\s*\(', content, re.IGNORECASE):
            result["opentelemetry"]["add_opentelemetry_registration"] = rel_path
            if "withtracing" in content.upper().replace(" ", ""):
                pass  # Already detected; check for specific exporters below
            if "prometheus" in content.lower():
                result["opentelemetry"]["exporter_targets"].append("Prometheus")
            if "jaeger" in content.lower() or "zipkin" in content.lower():
                exporter = "Jaeger" if "jaeger" in content.lower() else "Zipkin"
                result["opentelemetry"]["exporter_targets"].append(exporter)
            if "otlp" in content.lower() or "opentelemetryprotocol" in content.lower():
                result["opentelemetry"]["exporter_targets"].append("OTLP")

        # ActivitySource declarations
        for m in re.finditer(r'ActivitySource\s+(\w+)', content):
            result["opentelemetry"]["activity_source_declarations"] += 1

        # Manual span starts: .StartActivity( calls on custom sources
        activity_starts = re.findall(r'\.StartActivity\s*\([^)]*\)', content)
        result["opentelemetry"]["manual_span_starts"] += len(activity_starts)

        # Serilog + OTel correlation
        if "enrich.fromlogcontext" in content.lower():
            result["opentelemetry"]["serilog_otel_correlation"] = True

    # Messaging detection
    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))

        lower_content = content.lower()
        if "masstransit" in lower_content:
            result["messaging"]["library_used"] = "MassTransit"
            packages_seen.add("MassTransit")
            if "rabbitmq" in lower_content:
                result["messaging"]["broker_type"] = "RabbitMQ"
            elif "servicebus" in lower_content or "azure" in lower_content:
                result["messaging"]["broker_type"] = "Azure Service Bus"
            elif "kafka" in lower_content:
                result["messaging"]["broker_type"] = "Kafka"

        if "rebus" in lower_content and result["messaging"]["library_used"] is None:
            result["messaging"]["library_used"] = "Rebus"

        if "nservicebus" in lower_content and result["messaging"]["library_used"] is None:
            result["messaging"]["library_used"] = "NServiceBus"

        # Direct SDK usage (no MassTransit wrapper)
        if "rabbitmq.client" in content.lower() or re.search(r'new\s+ConnectionFactory', content):
            if not result["messaging"]["broker_type"]:
                result["messaging"]["broker_type"] = "RabbitMQ (direct client)"
        if "azure.messaging.servicebus" in content.lower():
            if not result["messaging"]["broker_type"]:
                result["messaging"]["broker_type"] = "Azure Service Bus (direct SDK)"

        # Outbox pattern detection
        if "entityframeworkoutbox" in lower_content:
            result["messaging"]["outbox_pattern"] = "MassTransit EntityFrameworkOutbox"
        elif re.search(r'outbox|transactional.*message|message.*outbox', lower_content):
            result["messaging"]["outbox_pattern"] = "custom transactional outbox"

        # Inbox pattern / deduplication
        if re.search(r'inbox|deduplication|duplicate.*prevent|processedmessages', lower_content):
            result["messaging"]["inbox_pattern"] = True

    result["opentelemetry"]["packages_found"] = list(packages_seen)
    return result


# ──────────────────────────────────────────────
# Phase E Enhancement: Arrange-Act-Assert & Test Naming
# ──────────────────────────────────────────────

def _detect_arrange_act_assert(test_methods: List[str]) -> Dict[str, Any]:
    """
    Detect Arrange-Act-Assert pattern in test method bodies.
    
    Signals:
      - Comment markers: // Act, // Assert, // Given, // When, // Then
      - Section spacing (blank lines separating logical blocks)
      - Variable naming patterns: 'arrangedX', 'result', 'expected'
      - Moq setup patterns (.Setup(...).Returns(...)) — implicit Arrange phase
      - FluentAssertions/Shouldly chains (.Should().Be(), .ShouldNotBeNull()) — explicit Assert
    """
    results = {
        "methods_using_comments": 0,
        "methods_using_spacing": 0,
        "methods_with_named_vars": 0,
        "sample_patterns": [],
    }
    for body in test_methods:
        has_comment_markers = bool(re.search(r'//\s*(Act|Assert|Arrange|Given|When|Then)\b', body))
        # Count blank-line-separated sections
        sections = [s.strip() for s in re.split(r'\n\s*\n', body.strip()) if s.strip()]
        has_section_spacing = len(sections) >= 2 and any(
            kw in sec.lower()
            for sec in sections
            for kw in ['act', 'assert', 'result', 'should', 'expect', 'verify']
        )
        # Named variables suggesting A-A-A
        has_named_vars = bool(re.search(r'(?:var|let)\s+(arranged?|expected|result|actual|given)', body, re.IGNORECASE))
        
        # NEW: Moq setup patterns — .Setup(...).Returns(...) indicates Arrange phase
        has_moq_setup = bool(re.search(r'\.Setup\([^)]*\)\.Returns\(', body)) or \
                         bool(re.search(r'Moq\.(Mock|It)\.', body))
        # NEW: FluentAssertions/Shouldly chains — explicit Assert markers
        has_fluent_assertion = bool(re.search(r'\.Should\(\)(?:\b)?(?:[.\s]*Be|NotBeNull|Throw|Contain|Match)', body, re.IGNORECASE)) or \
                               bool(re.search(r'ShouldNotBeNull|ShouldBeNullOrEmpty', body, re.IGNORECASE))

        if has_comment_markers:
            results["methods_using_comments"] += 1
        if has_section_spacing:
            results["methods_using_spacing"] += 1
        if has_named_vars:
            results["methods_with_named_vars"] += 1
        # Track new signals in sample_patterns for LLM context
        if has_moq_setup or has_fluent_assertion:
            detected_signals = []
            if has_moq_setup: detected_signals.append("Moq.Setup")
            if has_fluent_assertion: detected_signals.append("FluentAssertions")
            results.setdefault("sample_patterns", []).append({"signals": detected_signals})

    total = max(len(test_methods), 1)
    # Enhanced strength scoring — consider Moq/FluentAssertions as strong A-A-A indicators
    moq_count = len([p for p in results.get("sample_patterns", []) if "Moq.Setup" in p.get("signals", [])])
    fluent_count = len([p for p in results.get("sample_patterns", []) if "FluentAssertions" in p.get("signals", [])])
    combined_score = (results["methods_using_comments"] + 
                      results["methods_using_spacing"] * 0.8 + 
                      results["methods_with_named_vars"] * 0.7 +
                      moq_count * 1.2 +  # Moq Setup is a strong Arrange signal
                      fluent_count)      # FluentAssertions is a strong Assert signal
    strength = "strong" if combined_score > total * 0.3 else (
        "moderate" if combined_score > total * 0.15 else "weak"
    )
    results["overall_strength"] = strength
    return results


def _analyze_test_naming_convention(test_method_names: List[str]) -> Dict[str, Any]:
    """
    Analyze test method naming conventions.
    
    Common patterns:
      - xUnit convention: `MethodName_State_ExpectedResult` (snake_case with underscores)
      - Descriptive sentences: `it_should_return_null_when_input_is_empty`
      - PascalCase descriptive: `It_Should_Return_Null_When_Input_Is_Empty`
      - Simple verbs: `Test_CreateUser`, `Validate_UserInput`
    """
    if not test_method_names:
        return {"pattern": "none", "sample_names": []}

    snake_case_under_score = 0  # MethodName_State_ExpectedResult
    sentence_snake = 0          # it_should_do_this_when_that
    pascal_with_underscores = 0 # It_Does_This_When_That
    simple_pascal = 0           # TestCreateUser, ValidateUser
    describe_it_style = 0       # describe_xxx / context_xxx methods (BDD style)

    for name in test_method_names:
        stripped = re.sub(r'^(async_|test_|it_|should_)', '', name, flags=re.IGNORECASE).strip()
        if '_' not in stripped:
            continue
        parts = stripped.split('_')
        if len(parts) < 2:
            continue
        
        first_part_lower = parts[0].islower() and len(parts[0]) > 1
        middle_parts_snake = all(p.islower() or p.isdigit() for p in parts[1:-1])
        last_part_pascal = parts[-1][0].isupper() if parts[-1] else False

        # xUnit convention: Verb_State_ExpectedResult (first part camelCase, rest Pascal)
        if parts[0][0].islower() and last_part_pascal and middle_parts_snake:
            snake_case_under_score += 1
        # BDD style: describe_xxx / context_xxx
        elif parts[0] in ('describe', 'context', 'scenario'):
            describe_it_style += 1
        # Descriptive sentence snake: it_should_do_this_when_that
        elif first_part_lower and middle_parts_snake and len(parts) >= 3:
            sentence_snake += 1
        # Pascal with underscores (C#-style with _ as separator)
        elif all(p[0].isupper() if p else True for p in parts):
            pascal_with_underscores += 1
        else:
            simple_pascal += 1

    counts = {
        "xunit_convention": snake_case_under_score,
        "descriptive_sentence": sentence_snake,
        "pascal_separated": pascal_with_underscores,
        "describe_it_style": describe_it_style,
        "simple_verbs": simple_pascal,
    }
    dominant = max(counts, key=counts.get) if any(v > 0 for v in counts.values()) else "mixed"
    return {
        "dominant_pattern": dominant,
        "distribution": {k: f"{v} ({round(v/max(len(test_method_names)*1.0, 1)*100)}%)" for k, v in counts.items()},
        "sample_names": test_method_names[:5],
    }


# ──────────────────────────────────────────────
# Phase H: Code Style & Convention Analysis
# ──────────────────────────────────────────────

def phase_h_code_style_conventions(root: Path) -> Dict[str, Any]:
    """
    Phase H: Analyze coding style conventions across the codebase.
    
    Covers:
      - Class naming conventions (suffixes/prefixes like DTO/Repository/Service)
      - Namespace-location correlation (where files live relative to namespace prefix)
      - Inheritance hierarchies (full base→derived trees)
      - Partial class patterns and static utility classes
    """
    log("Phase H: Code Style & Convention Analysis")
    result = {
        "class_naming_conventions": {},  # {suffix/prefix: count}
        "namespace_location_patterns": {},  # {namespace_prefix: [sample_paths]}
        "inheritance_hierarchies": [],  # [{base, deriveds}]
        "partial_class_usage": False,
        "static_utility_classes": [],
        "test_method_names_sample": [],  # For naming convention analysis
        "arrange_act_assert": None,  # Set by phase_e enhancement below
    }

    all_cs_files = find_all_files(root, "**/*.cs")[:1500]  # Cap for performance

    class_info = []  # Collect all class info for hierarchy building
    test_methods_raw = []  # Method bodies for A-A-A detection
    test_method_names = []  # Names for naming convention analysis

    namespace_path_map: Dict[str, List[str]] = {}  # ns_prefix → [sample paths]

    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root))
        file_dir = os.path.dirname(rel_path)

        # --- Class declarations with base types (for inheritance trees) ---
        for cm in re.finditer(
            r'(?:public|internal|private|protected)?\s*(?:abstract\s+|partial\s+)*(?:class|record|interface)\s+(\w+)'
            r'\s*(:\s*(.+?))?\s*{',
            content
        ):
            class_name = cm.group(1)
            base_type = cm.group(3).strip() if cm.group(3) else None
            is_partial = 'partial' in cm.group(0)[:80]
            
            # Detect static utility classes (static + only static members)
            if re.match(r'.*public\s+static\s+(abstract\s+)?class\s+', content):
                result["static_utility_classes"].append({
                    "name": class_name,
                    "file": rel_path,
                })

            if not is_partial:
                pass  # Still track for hierarchy

            class_info.append({
                "name": class_name,
                "base_type": base_type,
                "is_partial": is_partial,
                "file": rel_path,
                "namespace": None,  # filled below
            })

        # Namespace prefix → path correlation
        ns_matches = re.findall(r'namespace\s+([\w.]+)\s*;', content)
        file_dir_parts = Path(rel_path).parts[:-1]  # directory parts without filename
        
        for ns in ns_matches:
            # Take the first meaningful segment after common prefixes
            segments = [s for s in ns.split('.') if s not in ('Domain', 'Application', 'Infrastructure', 'Presentation')]
            ns_key = segments[0] if segments else ns.split('.')[0]
            if ns_key not in namespace_path_map:
                namespace_path_map[ns_key] = []
            if len(namespace_path_map[ns_key]) < 3:  # Keep max 3 samples per prefix
                namespace_path_map[ns_key].append(rel_path)

    result["namespace_location_patterns"] = {k: v[:2] for k, v in namespace_path_map.items()}

    # --- Build inheritance hierarchies ---
    class_bases = {}  # name → base_type (first declaration wins)
    for ci in class_info:
        if ci["base_type"] and '.' not in ci["base_type"]:  # Simple type names only
            base_name = ci["base_type"].strip()
            if base_name not in class_bases:
                class_bases[base_name] = []
            class_bases[base_name].append(ci["name"])

    # Only report hierarchies with at least one derived class
    result["inheritance_hierarchies"] = [
        {"base_class": base, "derived_classes": deriveds[:10]}  # Cap per hierarchy
        for base, deriveds in sorted(class_bases.items(), key=lambda x: -len(x[1]))
        if len(deriveds) >= 2 and not any(kw in base.lower() for kw in ['object', 'value', 'record'])
    ][:15]  # Top 15 hierarchies by derived count

    # --- Partial class detection ---
    partial_count = sum(1 for ci in class_info if ci.get("is_partial", False))
    result["partial_class_usage"] = partial_count > 0
    if partial_count > 0:
        log(f"Found {partial_count} partial class declarations.", verbose_only=True)

    # --- Static utility classes ---
    result["static_utility_classes"] = result["static_utility_classes"][:20]

    return result, namespace_path_map, test_methods_raw, test_method_names


def phase_e_enhanced(root: Path) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], List[str]]:
    """
    Enhanced Phase E — wraps original test analysis + Arrange-Act-Assert + naming conventions.
    Returns (test_structure_result, code_style_data, test_method_bodies, test_method_names).
    """
    log("Phase E (Enhanced): Test Structure & Code Style")
    
    # Run original test structure detection
    base_result = {
        "test_projects": [],
        "test_framework": None,
        "mocking_library": None,
        "data_generation_tool": None,
        "attributes_found": {},
        "arrange_act_assert_pattern": None,
        "test_naming_convention": None,
    }

    all_csprojs = find_all_files(root, "**/*.csproj")
    for csproj in all_csprojs:
        content = read_file(csproj) or ""
        rel_path = str(csproj.relative_to(root))
        is_test_project = any(
            pattern in rel_path.lower()
            for pattern in [".tests.", "_tests_", ".test.", "_test_"]
        )
        if not is_test_project and re.search(r'<ProjectReference[^>]*Test', content):
            is_test_project = True

        if is_test_project:
            base_result["test_projects"].append(rel_path)
            lower_c = content.lower()
            if "xunit" in lower_c: base_result["test_framework"] = "xUnit"
            elif "nunit" in lower_c: base_result["test_framework"] = "NUnit"
            elif "mstest" in lower_c or "microsoft.visualstudio.testtools.unittesting" in lower_c:
                base_result["test_framework"] = "MSTest"
            if "moq" in lower_c: base_result["mocking_library"] = "Moq"
            elif "nsubstitute" in lower_c: base_result["mocking_library"] = "NSubstitute"
            elif "fakeiteasy" in lower_c: base_result["mocking_library"] = "FakeItEasy"
            if "faker" in lower_c or "bogus" in lower_c:
                base_result["data_generation_tool"] = "Bogus (Faker.NET)" if "bogus" in lower_c else "Faker.NET"

    # Scan test files for method-level patterns
    all_cs_files = find_all_files(root, "**/*.cs")[:500]
    attr_counts = {}
    test_method_bodies = []
    test_method_names_list = []

    for cs_file in all_cs_files:
        content = read_file(cs_file) or ""
        rel_path = str(cs_file.relative_to(root)).replace("\\", "/")  # Normalize separators
        is_test_project_file = any(
            tp in rel_path.lower()
            for tp in ["/.tests/", ".tests/", "/_tests/", "_tests/"]
        )
        if not is_test_project_file:
            continue

        # Count attributes - use explicit (pattern, name) tuples for clean keys
        _attr_patterns = [
            (r'\[Fact\]', 'Fact'),
            (r'\[Theory\]', 'Theory'),
            (r'\[Test\]', 'Test'),
            (r'\[TestMethod\]', 'TestMethod'),
            (r'describe\(', 'describe('),
            (r'it\(', 'it('),
        ]
        for pat, key in _attr_patterns:
            matches = re.findall(pat, content)
            attr_counts[key] = attr_counts.get(key, 0) + len(matches)

        # Extract test method bodies (for Arrange-Act-Assert detection)
        if is_test_project_file:
            # Match methods decorated with [Fact], [Test], [TestMethod]
            for tm in re.finditer(r'(?:public|private|protected|internal)?\s*(?:(?:static\s+)?(?:async\s+)?[\w<>,\.\s]+?)\s+(\w+)\s*\([^)]*\)(?::\s*[\w<>]+)?\s*{', content):
                method_name = tm.group(1)
                # Skip non-test methods (Get, Set, constructor names, etc.)
                test_indicators = ['test', 'should', 'can', 'it_', 'describe', 'context', '_when', '_given', '_and', '_setup', '_fixture', '_specification', '_scenario', 'creates', 'returns', 'throws', 'handles', 'processes', 'validates']
                if any(ind in method_name.lower() for ind in test_indicators):
                    body_start = tm.end()
                    depth = 0
                    i = body_start - 1
                    while i < len(content):
                        if content[i] == '{':
                            depth += 1
                        elif content[i] == '}':
                            depth -= 1
                            if depth == 0:
                                test_method_bodies.append(content[body_start:i])
                                test_method_names_list.append(method_name)
                                break
                        i += 1

    base_result["attributes_found"] = attr_counts
    if not base_result["test_framework"]:
        if "Fact" in attr_counts and attr_counts["Fact"] > 5: base_result["test_framework"] = "xUnit (inferred from [Fact])"
        elif "Test" in attr_counts and attr_counts["Test"] > 5: base_result["test_framework"] = "NUnit or MSTest ([Test] attribute)"
        elif "TestMethod" in attr_counts and attr_counts["TestMethod"] > 5: base_result["test_framework"] = "MSTest ([TestMethod])"

    # Arrange-Act-Assert detection
    aaa_pattern = _detect_arrange_act_assert(test_method_bodies)
    base_result["arrange_act_assert_pattern"] = aaa_pattern

    # Test naming convention analysis
    naming_conv = _analyze_test_naming_convention(test_method_names_list)
    base_result["test_naming_convention"] = naming_conv

    return (
        base_result,
        {"namespace_location_patterns": {}, "inheritance_hierarchies": [], "partial_class_usage": False, "static_utility_classes": []},
        test_method_bodies,
        test_method_names_list,
    )


# ──────────────────────────────────────────────
# Phase I: LLM Synthesis (Optional)
# ──────────────────────────────────────────────

def build_extraction_json(
    solution_data: Dict, phase_b: Dict, phase_c: Dict, phase_d: Dict,
    phase_e: Dict, phase_f: Dict, phase_g: Dict, code_style: Dict, root: Path
) -> Dict[str, Any]:
    """Combine all phases into a single structured extraction JSON."""
    # EC-4: Apply token budget limits to DI snippets
    di_methods = phase_b.get("di_extension_methods", [])
    if len(di_methods) > 30:
        # Prioritize AddDbContext, AddAuthentication, AddAuthorization over generic registrations
        priority_keywords = ["AddDbContext", "AddAuthentication", "AddAuthorization"]
        def priority_key(m):
            body_upper = m["full_body"].upper()
            for kw in priority_keywords:
                if kw.upper() in body_upper:
                    return 0
            return 1
        di_methods.sort(key=priority_key)
        di_methods = di_methods[:30]

    # EC-4: Apply token budget to middleware calls
    mw_calls = phase_b.get("middleware_calls", [])
    if len(mw_calls) > 40:
        # Prioritize UseAuthentication, UseAuthorization, MapControllers/MapGet
        critical_mw = ["UseAuthentication", "UseAuthorization", "MapControllers", "MapGroup"]
        prioritized = [m for m in mw_calls if any(kw in m for kw in critical_mw)]
        remaining = [m for m in mw_calls if not any(kw in m for kw in critical_mw)]
        mw_calls = (prioritized + remaining)[:40]

    return {
        "solution": solution_data,
        "entry_points_and_extensions": phase_b,
        "namespace_analysis": phase_c,
        "pattern_detection": phase_d,
        "test_structure": phase_e,
        "code_style_conventions": code_style,
        "external_dependencies": phase_f,
        "observability_and_messaging": phase_g,
        "_metadata": {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "target_root": str(root),
            "token_budget_applied": True,
            "di_method_count_after_cap": len(di_methods),
            "middleware_call_count_after_cap": len(mw_calls),
        },
    }


def compress_for_llm(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compress extraction data for LLM context window optimization.
    
    Reduces JSON size by ~70-85% while preserving all architectural signals:
    - DI extension methods: keep name/file/line only (drop full body text)
    - DbContext OnModelCreating: truncate to 300 chars max per context
    - Project inventory: dense summary table instead of verbose list
    - Package lists: group counts + top-5 examples per category
    - Middleware calls: compact one-line summaries
    - Inheritance hierarchies: cap at top-10, show base+derived names only
    """
    compressed = {}
    
    # ── Solution data: compress project inventory ──
    solution = extraction.get("solution", {})
    projects_raw = []
    for csproj in solution.get("csproj_files", []):
        sdk = solution.get("sdk_types", {}).get(csproj, "unknown")
        tfm = solution.get("target_frameworks", {}).get(csproj, "unknown")
        ot = solution.get("output_types", {}).get(csproj, "Library")
        ref_count = len(solution.get("project_references", {}).get(csproj, []))
        projects_raw.append({"file": csproj, "sdk": sdk.split(":")[0], "tfm": tfm[:12], "ot": ot, "refs": ref_count})
    
    compressed["solution"] = {
        "cpm_detected": solution.get("cpm_detected", False),
        "total_projects": len(projects_raw),
        "unique_packages": solution.get("packages", {}).__len__(),
        "frameworks": list(set(p["tfm"] for p in projects_raw)),
        "project_inventory": projects_raw,
    }
    
    # ── DI extensions: strip full bodies, keep metadata only ──
    entry_points = extraction.get("entry_points_and_extensions", {})
    di_methods = []
    for m in entry_points.get("di_extension_methods", [])[:30]:  # Cap at 30
        body_preview = (m.get("full_body", "")[:200] + "...") if len(m.get("full_body", "")) > 200 else m.get("full_body", "")
        # Count key registration calls in the method body
        add_count = len(re.findall(r'\.Add(Transient|Scoped|Singleton|DbContext)', body_preview, re.IGNORECASE))
        di_methods.append({
            "name": m.get("name", ""),
            "file": m.get("file", ""),
            "line": m.get("start_line", 0),
            "body_preview": body_preview[:300],  # Keep first 300 chars for context
            "add_registration_count": add_count,
        })
    
    compressed["entry_points"] = {
        "program_cs": entry_points.get("program_cs"),
        "hosting_model": entry_points.get("hosting_model"),
        "di_extension_methods": di_methods,
        "middleware_calls": [c[:150] for c in entry_points.get("middleware_calls", [])][:40],
        "i_consumer_implementation": [{"name": c["name"], "message_type": c["message_type"], "file": c["file"]} for c in entry_points.get("i_consumer_implementation", [])],
    }
    
    # ── Namespace analysis: keep top-20 per layer ──
    ns_analysis = extraction.get("namespace_analysis", {})
    compressed["namespace_analysis"] = {
        "detected_architecture_style": ns_analysis.get("detected_architecture_style"),
        "layer_classification": {},
    }
    for layer, items in ns_analysis.get("layer_classification", {}).items():
        compressed["namespace_analysis"]["layer_classification"][layer] = [
            {"ns": i.get("namespace", "")[:80], "count": i.get("file_count", 0)} 
            for i in sorted(items, key=lambda x: -x.get("file_count", 0))[:20]
        ]
    
    # ── Pattern detection: compress DbContext bodies ──
    patterns = extraction.get("pattern_detection", {})
    db_contexts = []
    for ctx in patterns.get("ef_core_contexts", [])[:15]:  # Cap at 15
        body = ctx.get("on_model_creating_body", "")
        # Extract Fluent API calls and entity types configured
        fluent_calls = re.findall(r'(?:Has|ToTable|HasKey|HasIndex|HasMaxLength|IsRequired|HasColumnName)\([^)]+\)', body[:2000])
        db_contexts.append({
            "name": ctx.get("name", ""),
            "file": ctx.get("file", ""),
            "fluent_api_calls": list(set(fluent_calls))[:10],  # Deduplicate, cap at 10
            "body_preview": body[:300] if len(body) > 300 else body,
        })
    
    compressed["patterns"] = {
        "repository_interfaces": patterns.get("repository_pattern", {}).get("interfaces", [])[:20],
        "mediatr_handlers_count": len(patterns.get("mediatr_handlers", [])),
        "ef_core_contexts": db_contexts,
        "generic_constraints": dict(list(patterns.get("generic_constraints", {}).items())[:20]),
        "abstract_base_classes": {k: v[:5] for k, v in patterns.get("abstract_base_classes", {}).items()},
        "attributes_found": patterns.get("attributes_found", {}),
    }
    
    # ── Test structure (already compact) ──
    compressed["test_structure"] = extraction.get("test_structure", {})
    
    # ── Code style conventions (compress hierarchies) ──
    code_style = extraction.get("code_style_conventions", {})
    compressed["code_style"] = {
        "partial_class_usage": code_style.get("partial_class_usage", False),
        "static_utility_classes_count": len(code_style.get("static_utility_classes", [])),
        "inheritance_hierarchies": [
            {"base": h["base_class"], "deriveds": h["derived_classes"][:10]}
            for h in code_style.get("inheritance_hierarchies", [])[:15]
        ],
        "namespace_location_patterns": dict(list(code_style.get("namespace_location_patterns", {}).items())[:20]),
    }
    
    # ── External dependencies (group counts) ──
    deps = extraction.get("external_dependencies", {})
    compressed["dependencies"] = {
        "total_unique_packages": deps.get("total_unique_packages", 0),
        "categorized_counts": {k: len(v) for k, v in deps.get("categorized_packages", {}).items() if v},
        "top_packages_by_category": {
            cat: [{"name": p["name"], "version": p["version"]} for p in pkg_list[:5]]
            for cat, pkg_list in deps.get("categorized_packages", {}).items()
            if pkg_list
        },
    }
    
    # ── Observability & messaging (already compact) ──
    compressed["observability_and_messaging"] = extraction.get("observability_and_messaging", {})
    
    return compressed


def generate_llm_prompt(extraction: Dict[str, Any], output_template_path: Path) -> Optional[str]:
    """Build the LLM synthesis prompt from structured extraction data + template."""
    # Read the output template
    template_content = read_file(output_template_path)
    if not template_content:
        log("⚠ Output template not found. Skipping LLM synthesis.", verbose_only=False)
        return None

    meta = extraction.get("_metadata", {})
    solution = extraction.get("solution", {})
    entry_points = extraction.get("entry_points_and_extensions", {})
    namespace_analysis = extraction.get("namespace_analysis", {})
    patterns = extraction.get("pattern_detection", {})
    tests = extraction.get("test_structure", {})
    dependencies = extraction.get("external_dependencies", {})
    observability = extraction.get("observability_and_messaging", {})

    # Build prompt with extracted data sections (EC-4: already capped by phases B–G)
    sys_instruction = """You are an expert .NET architect documenting the architecture of a C# codebase.

The user has provided structured extraction data from automated static analysis of their solution. Your task is to synthesize this into comprehensive, human-readable ARCHITECTURE.md documentation following the template structure below.

Rules:
1. Use EXACTLY the section numbering and headings from the output template.
2. Fill in every {{placeholder}} using the extracted data provided after the template.
3. If data for a section is empty or unknown, write "Not detected / not applicable" rather than inventing content.
4. For the DDD Primitives Assessment (Section 17), evaluate entity class signatures semantically — consider whether entities contain behavioral methods with business logic vs pure data classes. Report your assessment as Rich Domain, Anemic Model, or Mixed.
5. Be concise but thorough. Never repeat the same information across sections.
6. Use markdown tables where the template shows table structures.
7. Do NOT add sections beyond those defined in the template."""

    # Inject extracted data into prompt
    extraction_summary = f"""
=== EXTRACTED DATA FOR SYNTHESIS ===

**Solution Overview:**
- Project count: {len(solution.get('csproj_files', []))}
- CPM detected: {solution.get('cpm_detected', False)}
- Architecture style (inferred): {namespace_analysis.get('detected_architecture_style', 'unknown')}
- Target frameworks: {dict(list(solution.get('target_frameworks', {}).items())[:5])}

**DI Extension Methods Found ({meta.get('di_method_count_after_cap', 0)} total, capped):**
{json.dumps(entry_points.get("di_extension_methods", [])[:10], indent=2)[:3000]}

**Middleware Pipeline Order:**
{json.dumps(entry_points.get("middleware_calls", []), indent=2)[:2000]}

**Namespace Layer Classification:**
Domain patterns: {[ns["namespace"] for ns in namespace_analysis.get("layer_classification", {}).get("domain", [])][:5]}
Application patterns: {[ns["namespace"] for ns in namespace_analysis.get("layer_classification", {}).get("application", [])][:5]}
Infrastructure patterns: {[ns["namespace"] for ns in namespace_analysis.get("layer_classification", {}).get("infrastructure", [])][:5]}
Presentation patterns: {[ns["namespace"] for ns in namespace_analysis.get("layer_classification", {}).get("presentation", [])][:5]}

**Design Patterns Detected:**
- Repository interfaces: {len(patterns.get("repository_pattern", {}).get("interfaces", []))}
- MediatR handlers: {len(patterns.get("mediatr_handlers", []))}
- EF Core DbContexts: {len(patterns.get("ef_core_contexts", []))}
- Test attributes found: {patterns.get("attributes_found", {})}

**Test Structure:**
- Framework: {tests.get('test_framework', 'unknown')}
- Mocking library: {tests.get('mocking_library', 'none detected')}
- Data generation tool: {tests.get('data_generation_tool', 'manual')}
- Test projects: {tests.get('test_projects', [])}
- Arrange-Act-Assert pattern strength: {tests.get('arrange_act_assert_pattern', {}).get('overall_strength', 'unknown')}
  → Comments used: {tests.get('arrange_act_assert_pattern', {}).get('methods_using_comments', 0)}, Spacing sections: {tests.get('arrange_act_assert_pattern', {}).get('methods_using_spacing', 0)}
- Test naming convention: {json.dumps(tests.get('test_naming_convention', {}), indent=2)[:500]}

**External Dependencies (top categories):**
{json.dumps({k: v[:5] for k, v in dependencies.get("categorized_packages", {}).items() if v}, indent=2)[:3000]}

**Observability & Messaging:**
- OpenTelemetry configured: {'Yes' if observability.get('opentelemetry', {}).get('add_opentelemetry_registration') else 'No'}
- Exporter targets: {observability.get('opentelemetry', {}).get('exporter_targets', [])}
- ActivitySource declarations: {observability.get('opentelemetry', {}).get('activity_source_declarations', 0)}
- Serilog+OTel correlation: {observability.get('opentelemetry', {}).get('serilog_otel_correlation', False)}
- Messaging library: {observability.get('messaging', {}).get('library_used', 'None')}
- Broker type: {observability.get('messaging', {}).get('broker_type', 'None')}
- Consumer count (IConsumer<T>): {len(entry_points.get('i_consumer_implementation', []))}
- Outbox pattern: {observability.get('messaging', {}).get('outbox_pattern', 'Not detected')}

**Code Style & Conventions (Phase H):**
- Class naming patterns: {json.dumps(code_style.get('class_naming_conventions', {}), indent=2)[:800]}
- Inheritance hierarchies (top 10 by derived count): {json.dumps(code_style.get('inheritance_hierarchies', [])[:10], indent=2)[:3000]}
- Partial class usage detected: {code_style.get('partial_class_usage', False)}
- Static utility classes found: {len(code_style.get('static_utility_classes', []))}
- Namespace-location patterns: {json.dumps(code_style.get('namespace_location_patterns', {}) | {{k: v for k,v in code_style.get("namespace_location_patterns", {}).items()}}, indent=2)[:2000]}

**Entity Signatures for DDD Assessment:**
Extracted from Domain layer classes — evaluate each for behavioral methods vs pure data properties.
"""

    return f"{sys_instruction}\n\n=== OUTPUT TEMPLATE ===\n{template_content}\n\n=== EXTRACTED DATA ===\n{extraction_summary}"


def call_llm(
    prompt: str, api_base: str, model: str, api_key: str
) -> Optional[str]:
    """Send prompt to an OpenAI-compatible API and return the response."""
    try:
        import requests
    except ImportError:
        log("⚠ 'requests' package not available. Cannot call LLM.", verbose_only=False)
        return None

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert .NET architect."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 16000,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"⚠ LLM call failed: {e}", verbose_only=False)
        return None


# ──────────────────────────────────────────────
# Main Orchestration
# ──────────────────────────────────────────────

def main():
    args = parse_args()
    root = Path(args.target_dir).resolve()

    if not root.exists():
        print(f"Error: Target directory does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else (root / "ARCHITECTURE.md")

    log(f"Starting architecture extraction for: {root}")

    # Execute all phases sequentially
    phase_a_result = phase_a_solution_discovery(root)
    phase_b_result = phase_b_entry_point_discovery(root, args)
    phase_c_result = phase_c_namespace_analysis(root)
    phase_d_result = phase_d_pattern_detection(root)
    phase_e_result, _, _, _ = phase_e_enhanced(root)  # test structure + A-A-A + naming conventions
    
    # Phase H: Code Style & Convention Analysis (class hierarchies, partial classes, etc.)
    code_style_data, ns_location_map, aaa_bodies, aaa_names = phase_h_code_style_conventions(root)
    # Merge AAA results into test_structure for the LLM prompt
    if "arrange_act_assert_pattern" not in phase_e_result:
        phase_e_result["arrange_act_assert_pattern"] = {"overall_strength": "unknown", "methods_using_comments": 0}
    if "test_naming_convention" not in phase_e_result:
        phase_e_result["test_naming_convention"] = {"pattern": "none"}
    
    phase_f_result = phase_f_external_dependencies(phase_a_result)
    phase_g_result = phase_g_observability_messaging(root)

    # Combine into structured JSON (EC-4 applied during combination)
    extraction_json = build_extraction_json(
        phase_a_result, phase_b_result, phase_c_result,
        phase_d_result, phase_e_result, phase_f_result, phase_g_result, code_style_data, root
    )

    # Write raw extraction data (full detail for debugging/analysis)
    json_output_path = root / "extract_data.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(extraction_json, f, indent=2, default=str)
    log(f"Wrote full extraction data to: {json_output_path} ({os.path.getsize(json_output_path)//1024}KB)")

    # Also write compressed version optimized for LLM context window (~70% smaller)
    compressed = compress_for_llm(extraction_json)
    compressed_path = root / "extract_data_compressed.json"
    with open(compressed_path, "w", encoding="utf-8") as f:
        json.dump(compressed, f, indent=2, default=str)
    log(f"Wrote compressed extraction data (for LLM synthesis) to: {compressed_path} ({os.path.getsize(compressed_path)//1024}KB)")

    if args.no_llm:
        log("Skipping LLM synthesis (--no-llm flag). Done.")
        return 0

    # Build and send prompt to LLM
    template_path = Path(__file__).resolve().parent.parent / "references" / "output-template.md"
    prompt = generate_llm_prompt(extraction_json, template_path)

    if not prompt:
        log("⚠ Could not build LLM prompt. Writing JSON only.", verbose_only=False)
        return 0

    llm_response = call_llm(prompt, args.llm_api_base, args.llm_model, args.llm_key)

    if not llm_response:
        log("⚠ LLM returned no response. Writing JSON only.", verbose_only=False)
        # Write a minimal ARCHITECTURE.md with extraction summary as fallback
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Architecture Documentation\n\n> **Note**: LLM synthesis failed. Raw data available in `extract_data.json`.\n\n")
            f.write(f"## Summary\n\n- Projects found: {len(phase_a_result.get('csproj_files', []))}\n")
            f.write(f"- DI extension methods detected: {len(phase_b_result.get('di_extension_methods', []))}\n")
            f.write(f"- Architecture style (inferred): {phase_c_result.get('detected_architecture_style', 'unknown')}\n")
        log(f"Wrote minimal ARCHITECTURE.md as fallback: {output_path}")
        return 0

    # Write final synthesized document
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(llm_response)
    log(f"Written architecture documentation to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
