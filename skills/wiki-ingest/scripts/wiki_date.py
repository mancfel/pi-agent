#!/usr/bin/env python3
"""
wiki_date.py — Output today's system date in YYYY-MM-DD format.

Usage:
    python wiki_date.py           # prints 2026-08-24
    python wiki_date.py --iso     # same (ISO 8601 compliant)
    python wiki_date.py --short   # same (for use in filenames)

Designed to be sourced by all other wiki scripts and LLM agent workflows
to ensure consistent date usage across the entire wiki pipeline.

ALWAYS use this script instead of hardcoding dates in any wiki operation.
The canonical date for ALL wiki create/update operations is the current
system date at time of execution — never a template or placeholder value.
"""

import sys
from datetime import datetime


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python wiki_date.py [--iso|--short]")
        print("Outputs today's system date in YYYY-MM-DD format.")
        print("")
        print("Options:")
        print("  --iso   Output ISO 8601 date (default, same as no flag)")
        print("  --short Same as iso; for use in filenames without spaces")
        print("")
        print("Example:")
        print('  echo $(python wiki_date.py)')
        print("  # Outputs: 2026-08-24")
        sys.exit(0)
    
    if "--short" in sys.argv or "--iso" in sys.argv:
        pass  # default format is already YYYY-MM-DD
    
    print(today)


if __name__ == "__main__":
    main()
