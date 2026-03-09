#!/usr/bin/env python3
"""
Build script for mul-agent.

Usage:
    python scripts/build.py [options]
"""

import subprocess
import sys
from pathlib import Path


def build():
    """Build the project"""
    print("Building mul-agent...")

    # Create dist directory
    dist_dir = Path(__file__).parent.parent / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Run any build steps here
    print("Build complete!")


if __name__ == "__main__":
    build()
