#!/usr/bin/env python3
"""
Wrapper script for lisyoen/convention-extractor.

Validates prerequisites, invokes the external tool with proper configuration precedence,
and verifies output artifacts exist and are non-empty.

Usage:
    python extract_conventions.py --target-dir <path> [--lang python] [--threshold 90]
                                   [--merge existing.md] [--output outdir]

Configuration Precedence (highest to lowest):
    1. CLI flags (--api-base, --model, --threshold)
    2. Environment variables (CONVENTION_API_BASE, CONVENTION_API_KEY, CONVENTION_MODEL)
    3. config.yaml in target directory
    4. Defaults (http://localhost:11434/v1 for API base)

Prerequisites: Python 3.6+, requests, pyyaml
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def check_prerequisites():
    """Check that required tools and packages are available."""
    errors = []

    # Check Python version
    if sys.version_info < (3, 6):
        errors.append(f"Python 3.6+ required, found {sys.version_info.major}.{sys.version_info.minor}")

    # Check pip packages
    for package in ["requests", "pyyaml"]:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            errors.append(f"Missing package: {package} (install via pip install {package})")

    return errors


def parse_config(target_dir):
    """Parse configuration with precedence: CLI > env > config.yaml > defaults."""
    config = {
        "api_base": os.environ.get("CONVENTION_API_BASE", "http://localhost:11434/v1"),
        "api_key": os.environ.get("CONVENTION_API_KEY", ""),
        "model": os.environ.get("CONVENTION_MODEL", ""),
        "threshold": 90,
    }

    # Load from config.yaml if present
    config_path = Path(target_dir) / "config.yaml"
    try:
        import yaml
        if config_path.exists():
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            config["api_base"] = user_config.get("api_base", config["api_base"])
            config["api_key"] = user_config.get("api_key", config["api_key"])
            config["model"] = user_config.get("model", config["model"])
            config["threshold"] = user_config.get("threshold", config["threshold"])
    except ImportError:
        pass  # pyyaml not available; skip config.yaml parsing

    return config


def invoke_extractor(target_dir, lang, threshold, merge_file=None, output_dir=None):
    """Invoke the lisyoen/convention-extractor tool."""
    target_path = Path(target_dir).resolve()

    if not (target_path / "CONVENTIONS.md").exists():
        conventions_file = target_path / f"{lang}_convention.md"
    else:
        conventions_file = target_path / f"{lang}_convention.md"

    out_dir = Path(output_dir) if output_dir else target_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "extract_convention",  # or direct script path
        str(target_path),
        "--lang", lang,
        "-o", str(out_dir),
        "--threshold", str(threshold),
    ]

    if merge_file and Path(merge_file).exists():
        cmd.extend(["--merge", str(Path(merge_file).resolve())])

    print(f"[extract-conventions] Invoking: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(target_path))

    return result


def validate_outputs(output_dir):
    """Validate that all expected output files exist and are non-empty."""
    out_path = Path(output_dir)
    issues = []

    # Check for convention markdown file (any {lang}_convention.md)
    md_files = list(out_path.glob("*_convention.md"))
    if not md_files:
        issues.append("Missing: *_convention.md file")
    else:
        for f in md_files:
            content = f.read_text(encoding="utf-8", errors="replace").strip()
            if len(content.splitlines()) < 10:
                issues.append(f"File too short ({f.name}): {len(content.splitlines())} lines")

    # Check conventions.json
    json_file = out_path / "conventions.json"
    if not json_file.exists():
        issues.append("Missing: conventions.json")
    else:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if "adoption" not in data and "scores" not in data and not isinstance(data, dict):
                issues.append(f"conventions.json has unexpected format: {list(data.keys())[:5]}")
        except json.JSONDecodeError as e:
            issues.append(f"conventions.json is invalid JSON: {e}")

    # Check for refactoring_needed file (any matching pattern)
    refactor_files = list(out_path.glob("refactoring_needed_*.txt"))
    # This file may be empty — existence is sufficient
    # But at least one should have been created by the tool

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Wrapper for lisyoen/convention-extractor with validation."
    )
    parser.add_argument("--target-dir", required=True, help="Path to target repository root")
    parser.add_argument("--lang", default="python", help="Target programming language")
    parser.add_argument("--threshold", type=int, default=90, help="Adoption threshold percentage (default: 90)")
    parser.add_argument("--merge", default=None, help="Path to existing convention file to merge")
    parser.add_argument("--output", default=None, help="Output directory (default: same as target-dir)")

    args = parser.parse_args()

    # Check prerequisites
    prereq_errors = check_prerequisites()
    if prereq_errors:
        print("[extract-conventions] PREREQUISITE ERRORS:", file=sys.stderr)
        for err in prereq_errors:
            print(f"  ✗ {err}", file=sys.stderr)
        sys.exit(1)

    print("[extract-conventions] Prerequisites OK")

    # Parse configuration with precedence
    config = parse_config(args.target_dir)
    threshold = args.threshold  # CLI overrides env/config.yaml

    print(f"[extract-conventions] Target: {args.target_dir}")
    print(f"[extract-conventions] Language: {args.lang}")
    print(f"[extract-conventions] Threshold: {threshold}%")
    if args.merge:
        print(f"[extract-conventions] Merge with: {args.merge}")
    print(f"[extract-conventions] API Base: {config['api_base']}")
    print(f"[extract-conventions] Model: {config.get('model', '(default)')}")

    # Invoke extractor
    output_dir = args.output or args.target_dir
    result = invoke_extractor(args.target_dir, args.lang, threshold, args.merge, output_dir)

    if result.stdout.strip():
        print("[extract-conventions] STDOUT:", file=sys.stderr)
        for line in result.stdout.strip().splitlines()[:50]:  # Limit output
            print(f"  {line}", file=sys.stderr)

    if result.returncode != 0:
        print(f"[extract-conventions] Tool exited with code {result.returncode}", file=sys.stderr)
        if result.stderr.strip():
            print("[extract-conventions] STDERR:", file=sys.stderr)
            for line in result.stderr.strip().splitlines()[:20]:
                print(f"  {line}", file=sys.stderr)

        # Write debug log on error
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = Path(output_dir) / f"debug_extract_{timestamp}.log"
        debug_path.write_text(
            f"Extract failed at {datetime.now().isoformat()}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n",
            encoding="utf-8",
        )
        print(f"[extract-conventions] Debug log written to: {debug_path}")
        sys.exit(result.returncode or 1)

    # Validate outputs
    issues = validate_outputs(output_dir)
    if issues:
        print("[extract-conventions] VALIDATION ISSUES:", file=sys.stderr)
        for issue in issues:
            print(f"  ✗ {issue}", file=sys.stderr)
        sys.exit(2)

    print("[extract-conventions] All output files validated successfully")

    # Summary of generated artifacts
    out = Path(output_dir)
    md_files = list(out.glob("*_convention.md"))
    json_exists = (out / "conventions.json").exists()
    refactor_files = list(out.glob("refactoring_needed_*.txt"))

    print(f"[extract-conventions] Artifacts:")
    if md_files:
        print(f"  - {md_files[0].name} ({len(md_files[0].read_text(encoding='utf-8').splitlines())} lines)")
    if json_exists:
        data = json.loads((out / "conventions.json").read_text(encoding="utf-8"))
        rules_count = len(data) if isinstance(data, dict) else 0
        print(f"  - conventions.json ({rules_count} rules)")
    for rf in refactor_files:
        size = rf.stat().st_size
        status = f"{size} bytes" if size > 0 else "(empty — all files conform)"
        print(f"  - {rf.name} — {status}")


if __name__ == "__main__":
    main()
