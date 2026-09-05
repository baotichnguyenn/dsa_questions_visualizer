"""Puts the practice root on sys.path so `from harness import ...` resolves.

One copy, at the root - pytest loads every conftest.py between rootdir and a
test file's own folder, so this covers test_problems.py and every problem's
tests.py without a per-folder copy.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
