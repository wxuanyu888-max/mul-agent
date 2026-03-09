#!/usr/bin/env python3
"""
Lint script for mul-agent.

Usage:
    python scripts/lint.py [options]
"""

import subprocess
import sys
from pathlib import Path


def run_lint():
    """Run linting"""
    print("Running linters...")

    # Ruff check
    print("\n[Ruff] Checking...")
    subprocess.run([sys.executable, "-m", "ruff", "check", "src/", "tests/"])

    # Ruff format check
    print("\n[Ruff] Formatting...")
    subprocess.run([sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/"])

    print("\nLint complete!")


if __name__ == "__main__":
    run_lint()
