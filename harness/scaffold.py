"""Create a new problem folder from the template."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import theme as T
from .discovery import ROOT

TEMPLATE = ROOT / "_template"


def slugify(name: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()
    return slug or "new_problem"


def create(name: str, root: Path = ROOT) -> Path:
    slug = slugify(name)
    target = root / slug
    if target.exists():
        raise FileExistsError(f"{slug} already exists at {target}")
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template folder missing: {TEMPLATE}")

    shutil.copytree(TEMPLATE, target)
    title = slug.replace("_", " ").title()
    for path in target.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".py", ".md"):
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("{{TITLE}}", title).replace("{{SLUG}}", slug),
                encoding="utf-8",
            )
    return target


def announce(target: Path) -> None:
    print()
    print("  " + T.paint(f"{T.TICK} Created {target.name}/", T.GREEN))
    print()
    for filename, purpose in (
        ("question.md", "paste the problem statement here"),
        ("solution.py", "write your solution here"),
        ("tests.py", "add testcases here (ENTRY_POINT + TEST_CASES)"),
        ("judge.py", "run this to judge this problem"),
        ("test_algorithm.py", "pytest adapter, no edits needed"),
        ("conftest.py", "import paths for pytest, no edits needed"),
    ):
        print("    " + T.paint(filename.ljust(20), T.WHITE) + T.paint(purpose, T.MUTED))
    print()
    print("  " + T.paint("Judge it with any of:", T.MUTED))
    print("    " + T.paint(f"python practice.py {target.name}", T.WHITE)
          + T.paint("   from here", T.MUTED))
    print("    " + T.paint(f"cd {target.name} && python judge.py", T.WHITE)
          + T.paint("   from the folder", T.MUTED))
    print("    " + T.paint("Ctrl+Shift+B", T.WHITE)
          + T.paint("   in VSCode, with one of its files open", T.MUTED))
    print()
