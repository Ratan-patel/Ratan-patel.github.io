#!/usr/bin/env python3
"""Convenience launcher so AIRT runs from any directory without installing.

    python3 tools/ai-redteam-scanner/airt-cli.py demo
    python3 tools/ai-redteam-scanner/airt-cli.py scan --target-type http ...

Equivalent to `cd tools/ai-redteam-scanner && python3 -m airt ...`
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from airt.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
