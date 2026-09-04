"""Runs one problem's solution against its testcases inside a child process.

Isolated on purpose: an infinite loop, a sys.exit(), or a hard crash in the
solution cannot take the UI down with it. Results leave as JSON.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import time
import traceback
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.casedef import brief, load_cases  # noqa: E402
from harness.loader import import_from, tests_path  # noqa: E402
from harness.scaling import measure  # noqa: E402

STDOUT_LIMIT = 2000


def _describe(exc: BaseException, origin: Path) -> Dict[str, Any]:
    """Pull out the frame that belongs to the user's own file, if there is one."""
    frames = traceback.extract_tb(exc.__traceback__)
    own = [f for f in frames if Path(f.filename).resolve() == origin]
    frame = own[-1] if own else (frames[-1] if frames else None)
    detail: Dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
        "line": None,
        "func": None,
        "code": None,
        "file": None,
    }
    if isinstance(exc, SyntaxError) and exc.lineno:
        detail["line"] = exc.lineno
        detail["code"] = (exc.text or "").strip() or None
        detail["file"] = Path(exc.filename).name if exc.filename else origin.name
    elif frame is not None:
        detail["line"] = frame.lineno
        detail["func"] = frame.name
        detail["code"] = (frame.line or "").strip() or None
        detail["file"] = Path(frame.filename).name
    return detail


def _resolve_entry(module, tests_module, solution_path: Path):
    name = getattr(tests_module, "ENTRY_POINT", None)
    if name:
        fn = getattr(module, name, None)
        if fn is None:
            raise AttributeError(
                f"{solution_path.name} does not define {name}() "
                "- the name comes from ENTRY_POINT in tests.py"
            )
        return name, fn
    candidates = [
        (attr, obj)
        for attr, obj in vars(module).items()
        if callable(obj)
        and not attr.startswith("_")
        and getattr(obj, "__module__", None) == module.__name__
    ]
    if len(candidates) == 1:
        return candidates[0]
    found = ", ".join(n for n, _ in candidates) or "nothing"
    raise AttributeError(
        f"Set ENTRY_POINT in tests.py - cannot infer which function to call (found: {found})"
    )


DEFAULT_SCALING_SIZES = (1000, 2000, 4000, 8000, 16000)


def _scaling_for(tests_module, fn) -> Optional[Dict[str, Any]]:
    """Measure how the solution scales, if tests.py says how to size an input."""
    build = getattr(tests_module, "scaling_input", None)
    if build is None:
        return None
    sizes = list(getattr(tests_module, "SCALING_SIZES", DEFAULT_SCALING_SIZES))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return measure(fn, build, sizes)
    except BaseException as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "rows": [],
                "time": None, "space": None}


def run(problem_dir: Path, with_scaling: bool = False) -> Dict[str, Any]:
    solution_path = (problem_dir / "solution.py").resolve()
    tests_path_found = tests_path(problem_dir)

    result: Dict[str, Any] = {
        "slug": problem_dir.name,
        "entry_point": None,
        "load_error": None,
        "cases": [],
        "total_ms": 0.0,
        "peak_kb": None,
        "scaling": None,
    }

    if str(problem_dir) not in sys.path:
        sys.path.insert(0, str(problem_dir))

    if tests_path_found is None:
        result["load_error"] = {
            "type": "FileNotFoundError",
            "message": f"No tests.py found in {problem_dir.name}",
            "line": None, "func": None, "code": None, "file": None,
            "phase": "tests",
        }
        return result

    try:
        tests_module = import_from(tests_path_found, f"_tests_{problem_dir.name}")
        cases = load_cases(tests_module)
    except BaseException as exc:
        detail = _describe(exc, tests_path_found)
        detail["phase"] = "tests"
        result["load_error"] = detail
        return result

    try:
        solution_module = import_from(solution_path, f"_solution_{problem_dir.name}")
        entry_name, fn = _resolve_entry(solution_module, tests_module, solution_path)
        result["entry_point"] = entry_name
    except BaseException as exc:
        detail = _describe(exc, solution_path)
        detail["phase"] = "solution"
        result["load_error"] = detail
        return result

    records: List[Dict[str, Any]] = []
    tracemalloc.start()
    grand_total = 0.0

    for index, tcase in enumerate(cases):
        record: Dict[str, Any] = {
            "index": index,
            "name": tcase.name,
            "args_repr": {k: brief(v) for k, v in tcase.args.items()},
            "expected_repr": brief(tcase.expected),
            "status": "pass",
            "output_repr": None,
            "stdout": "",
            "error": None,
            "runtime_ms": 0.0,
        }
        call_args = copy.deepcopy(tcase.positional)
        buffer = io.StringIO()
        started = time.perf_counter()
        try:
            with contextlib.redirect_stdout(buffer):
                actual = fn(*call_args)
            record["runtime_ms"] = (time.perf_counter() - started) * 1000
            record["output_repr"] = brief(actual)
            if not tcase.matches(actual):
                record["status"] = "fail"
        except BaseException as exc:
            record["runtime_ms"] = (time.perf_counter() - started) * 1000
            record["status"] = "error"
            record["error"] = _describe(exc, solution_path)
        grand_total += record["runtime_ms"]
        text = buffer.getvalue()
        if len(text) > STDOUT_LIMIT:
            text = text[:STDOUT_LIMIT] + "\n... (output truncated)"
        record["stdout"] = text
        records.append(record)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result["cases"] = records
    result["total_ms"] = grand_total
    result["peak_kb"] = peak / 1024

    # Only worth measuring a solution that is actually correct.
    if with_scaling and all(r["status"] == "pass" for r in records):
        result["scaling"] = _scaling_for(tests_module, fn)

    return result


def main() -> int:
    problem_dir = Path(sys.argv[1]).resolve()
    out_path = Path(sys.argv[2])
    with_scaling = "--scaling" in sys.argv[3:]
    try:
        payload = run(problem_dir, with_scaling=with_scaling)
    except BaseException as exc:  # last resort, keep the parent informed
        payload = {
            "slug": problem_dir.name,
            "entry_point": None,
            "load_error": {
                "type": type(exc).__name__, "message": str(exc), "phase": "harness",
                "line": None, "func": None, "code": None, "file": None,
            },
            "cases": [], "total_ms": 0.0, "peak_kb": None, "scaling": None,
        }
    out_path.write_text(json.dumps(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
