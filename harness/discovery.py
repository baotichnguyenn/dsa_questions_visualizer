"""Locate problem folders sitting next to the harness."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent

TESTS_NAMES = ("tests.py", "testcases.py")
QUESTION_GLOBS = ("question*.md", "question*.MD", "README.md", "*.md", "*.MD")
SKIP_DIRS = {"harness", "_template", "__pycache__", ".pytest_cache", ".git", ".venv", "venv"}


@dataclass
class Problem:
    slug: str
    path: Path

    @property
    def solution(self) -> Path:
        return self.path / "solution.py"

    @property
    def tests(self) -> Optional[Path]:
        for name in TESTS_NAMES:
            candidate = self.path / name
            if candidate.exists():
                return candidate
        return None

    @property
    def question(self) -> Optional[Path]:
        for pattern in QUESTION_GLOBS:
            for hit in sorted(self.path.glob(pattern)):
                return hit
        return None

    @property
    def title(self) -> str:
        return self.slug.replace("_", " ").replace("-", " ").title()

    def watched_files(self) -> List[Path]:
        return [p for p in (self.solution, self.tests) if p and p.exists()]


def _is_problem(path: Path) -> bool:
    if not path.is_dir() or path.name in SKIP_DIRS or path.name.startswith("."):
        return False
    return (path / "solution.py").exists()


def discover(root: Path = ROOT) -> List[Problem]:
    return [
        Problem(slug=p.name, path=p)
        for p in sorted(root.iterdir(), key=lambda q: q.name.lower())
        if _is_problem(p)
    ]


def _as_directory(target: str) -> Optional[Path]:
    """Resolve `target` to a directory, or None if it is not a usable path.

    A file resolves to the folder holding it, so an editor can hand us the file
    it happens to have open rather than the problem folder.
    """
    try:
        resolved = Path(target).expanduser().resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    try:
        if resolved.is_file():
            return resolved.parent
        if resolved.is_dir():
            return resolved
    except OSError:
        return None
    return None


def find(target: str, root: Path = ROOT) -> Optional[Problem]:
    """Look a problem up by slug, or by any path pointing into its folder.

    Accepts 'nested_transcript', a tab-completed 'nested_transcript/', '.', an
    absolute folder, or an absolute file inside the folder.
    """
    problems = discover(root)

    directory = _as_directory(target)
    if directory is not None:
        for problem in problems:
            try:
                if problem.path.resolve() == directory:
                    return problem
            except OSError:
                continue

    # Fall back to the folder name: trailing separators from shell completion,
    # and any leading path that did not resolve, are not part of the slug.
    name = target.replace("\\", "/").rstrip("/").rpartition("/")[2] or target
    for problem in problems:
        if problem.slug.lower() == name.lower():
            return problem
    partial = [p for p in problems if name.lower() in p.slug.lower()]
    return partial[0] if len(partial) == 1 else None
