"""pytest view of the very same testcases the judge uses.

    python -m pytest test_algorithm.py -q        (from this folder)
    python -m pytest -q                          (from the practice root)

There is nothing to edit here - add testcases in tests.py.
"""
import pytest

from harness.casedef import load_cases
from harness.loader import problem_modules

solution, tests = problem_modules(__file__)
CASES = load_cases(tests)
FUNCTION = getattr(solution, tests.ENTRY_POINT)


@pytest.mark.parametrize("case", CASES, ids=[c.name for c in CASES])
def test_case(case):
    actual = FUNCTION(*case.positional)
    shown = ", ".join("{} = {!r}".format(k, v) for k, v in case.args.items())
    assert case.matches(actual), (
        "\n"
        "Case:     {}\n"
        "Input:    {}\n"
        "Expected: {!r}\n"
        "Received: {!r}\n".format(case.name, shown, case.expected, actual)
    )
