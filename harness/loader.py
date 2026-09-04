"""Import a problem's solution.py / tests.py by path.

By path, and under a name qualified by the folder, so two problem folders that
both contain 'solution.py' never collide in sys.modules.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Tuple

TESTS_NAMES = ("tests.py", "testcases.py")


def import_from(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def add_to_path(problem_dir: Path) -> None:
    """So a solution can import its own helper modules."""
    root = problem_dir.parent
    for entry in (problem_dir, root):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))


def tests_path(problem_dir: Path):
    for name in TESTS_NAMES:
        candidate = problem_dir / name
        if candidate.exists():
            return candidate.resolve()
    return None


def problem_modules(anchor: str) -> Tuple[object, object]:
    """Load (solution, tests) for the problem folder holding `anchor`.

    `anchor` is a file inside the problem folder - pass __file__.
    """
    problem_dir = Path(anchor).resolve().parent
    add_to_path(problem_dir)
    slug = problem_dir.name
    found = tests_path(problem_dir)
    if found is None:
        raise FileNotFoundError(f"No tests.py in {slug}")
    tests = import_from(found, f"_tests_{slug}")
    solution = import_from((problem_dir / "solution.py").resolve(), f"_solution_{slug}")
    return solution, tests
