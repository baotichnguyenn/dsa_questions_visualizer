#!/usr/bin/env python3
"""Judge this problem, without leaving its folder.

    python judge.py         judge once
    python judge.py -w      re-judge every time you save
    python judge.py -a      a detail panel for every failing case, not just the first

Identical to running `python practice.py <this folder>` from the practice root.
Nothing to edit here.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from practice import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main([str(HERE), *sys.argv[1:]]))
