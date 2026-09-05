"""pytest view of every problem in problems/, over the exact same testcases
the judge uses.

    python -m pytest -q                              every problem
    python -m pytest test_problems.py -q -k nested    one problem, by slug

One file for the whole repo - what used to be a test_algorithm.py duplicated
into every problem folder. Nothing to edit here or in any problem folder to
get pytest coverage; add testcases in a problem's tests.py and this picks
them up automatically.
"""
from __future__ import annotations

import pytest

from harness.casedef import load_cases
from harness.discovery import discover
from harness.loader import problem_modules


def _collect():
    """One entry per testcase, or one failing placeholder per problem whose
    solution.py / tests.py won't even import - so a broken problem shows up
    as a single clear failure instead of taking every other problem's tests
    down with it."""
    items = []
    for problem in discover():
        if problem.tests is None:
            continue
        try:
            solution, tests = problem_modules(str(problem.solution))
            function = getattr(solution, tests.ENTRY_POINT)
            cases = load_cases(tests)
        except BaseException as exc:  # noqa: BLE001 - surfaced as a test failure below
            items.append((problem.slug, None, None, exc))
            continue
        for case in cases:
            items.append((problem.slug, function, case, None))
    return items


def pytest_generate_tests(metafunc):
    if "problem_case" not in metafunc.fixturenames:
        return
    collected = _collect()
    ids = [
        f"{slug}::<load error>" if load_error else f"{slug}::{case.name}"
        for slug, _fn, case, load_error in collected
    ]
    metafunc.parametrize("problem_case", collected, ids=ids)


def test_case(problem_case):
    slug, function, case, load_error = problem_case
    if load_error is not None:
        pytest.fail(f"{slug}: could not load - {type(load_error).__name__}: {load_error}")

    actual = function(*case.positional)
    shown = ", ".join(f"{k} = {v!r}" for k, v in case.args.items())
    assert case.matches(actual), (
        "\n"
        f"Problem:  {slug}\n"
        f"Case:     {case.name}\n"
        f"Input:    {shown}\n"
        f"Expected: {case.expected!r}\n"
        f"Received: {actual!r}\n"
    )
