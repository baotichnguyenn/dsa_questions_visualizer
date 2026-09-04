"""Testcases for {{TITLE}}.

ENTRY_POINT   the function in solution.py that gets called.
TEST_CASES    one case() per testcase. Every keyword other than `expected`
              becomes an argument, passed in the order you write it:

                  case("Example 1", expected=[0, 1], nums=[2, 7, 11], target=9)
                  -> calls  two_sum([2, 7, 11], 9)  and compares against [0, 1]
"""
from harness import case

ENTRY_POINT = "solve"

TEST_CASES = [
    case(
        "Example 1",
        expected=None,
        data=[],
    ),
]


# Optional. Once every testcase passes, the results window measures how your
# solution actually scales and names the complexity class it matches. Return
# the arguments for one run of size n, then uncomment both.
#
# SCALING_SIZES = [2000, 4000, 8000, 16000, 32000]
#
# def scaling_input(n):
#     return {"data": list(range(n))}
