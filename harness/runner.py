"""Parent side of the run: spawn the worker, enforce a timeout, build a verdict."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .discovery import ROOT, Problem

ACCEPTED = "Accepted"
WRONG_ANSWER = "Wrong Answer"
RUNTIME_ERROR = "Runtime Error"
COMPILE_ERROR = "Compile Error"
TIME_LIMIT = "Time Limit Exceeded"
HARNESS_ERROR = "Harness Error"

DEFAULT_TIMEOUT = 10.0
COMPILE_ERRORS = {"SyntaxError", "IndentationError", "TabError"}


@dataclass
class CaseResult:
    index: int
    name: str
    args_repr: Dict[str, str]
    expected_repr: str
    status: str                      # pass | fail | error
    output_repr: Optional[str]
    stdout: str
    error: Optional[Dict[str, Any]]
    runtime_ms: float

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    @property
    def number(self) -> int:
        return self.index + 1


@dataclass
class Submission:
    problem: Problem
    verdict: str
    cases: List[CaseResult] = field(default_factory=list)
    runtime_ms: float = 0.0
    peak_kb: Optional[float] = None
    load_error: Optional[Dict[str, Any]] = None
    entry_point: Optional[str] = None
    scaling: Optional[Dict[str, Any]] = None

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.ok)

    @property
    def accepted(self) -> bool:
        return self.verdict == ACCEPTED

    @property
    def failures(self) -> List[CaseResult]:
        return [c for c in self.cases if not c.ok]

    @property
    def first_failure(self) -> Optional[CaseResult]:
        return self.failures[0] if self.failures else None


def _verdict_for(cases: List[CaseResult]) -> str:
    """LeetCode semantics: the first failing case decides the verdict."""
    for case_result in cases:
        if case_result.status == "error":
            kind = (case_result.error or {}).get("type", "")
            return COMPILE_ERROR if kind in COMPILE_ERRORS else RUNTIME_ERROR
        if case_result.status == "fail":
            return WRONG_ANSWER
    return ACCEPTED


def submit(problem: Problem, timeout: float = DEFAULT_TIMEOUT,
           with_scaling: bool = False) -> Submission:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        out_path = Path(handle.name)
    extra = ["--scaling"] if with_scaling else []
    try:
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "harness.worker",
             str(problem.path), str(out_path), *extra],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        out_path.unlink(missing_ok=True)
        return Submission(
            problem=problem,
            verdict=TIME_LIMIT,
            load_error={
                "type": "TimeLimitExceeded",
                "message": f"Execution exceeded {timeout:g}s - likely an infinite loop.",
                "phase": "solution", "line": None, "func": None, "code": None, "file": None,
            },
        )

    try:
        raw = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    finally:
        out_path.unlink(missing_ok=True)

    if not raw:
        detail = (completed.stderr or "").strip() or "The worker produced no result."
        return Submission(
            problem=problem,
            verdict=HARNESS_ERROR,
            load_error={
                "type": "WorkerCrash", "message": detail, "phase": "harness",
                "line": None, "func": None, "code": None, "file": None,
            },
        )

    payload = json.loads(raw)
    cases = [
        CaseResult(
            index=item["index"],
            name=item["name"],
            args_repr=item["args_repr"],
            expected_repr=item["expected_repr"],
            status=item["status"],
            output_repr=item["output_repr"],
            stdout=item["stdout"],
            error=item["error"],
            runtime_ms=item["runtime_ms"],
        )
        for item in payload["cases"]
    ]

    load_error = payload.get("load_error")
    if load_error:
        kind = load_error.get("type", "")
        verdict = COMPILE_ERROR if kind in COMPILE_ERRORS else RUNTIME_ERROR
        if load_error.get("phase") in ("tests", "harness"):
            verdict = HARNESS_ERROR
    else:
        verdict = _verdict_for(cases)

    return Submission(
        problem=problem,
        verdict=verdict,
        cases=cases,
        runtime_ms=payload.get("total_ms", 0.0),
        peak_kb=payload.get("peak_kb"),
        load_error=load_error,
        entry_point=payload.get("entry_point"),
        scaling=payload.get("scaling"),
    )
