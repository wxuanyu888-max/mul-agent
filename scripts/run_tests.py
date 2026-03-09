#!/usr/bin/env python3
"""
Run tests for mul-agent.

Usage:
    python scripts/run_tests.py [options]

Options:
    --coverage    Run with coverage
    --watch       Watch mode
    --verbose     Verbose output
"""

import subprocess
import sys
from pathlib import Path


def run_tests(coverage: bool = False, watch: bool = False, verbose: bool = False):
    """Run tests"""
    cmd = [sys.executable, "-m", "pytest"]

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])

    if watch:
        cmd.append("--watch")

    if verbose:
        cmd.append("-v")

    # Add test paths
    test_paths = ["tests/", "src/"]
    for path in test_paths:
        if Path(path).exists():
            cmd.append(path)

    subprocess.run(cmd)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--watch", action="store_true", help="Watch mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()
    run_tests(**vars(args))
