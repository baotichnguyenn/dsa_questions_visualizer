"""Testcases for the nested cryptographic transcript problem.

Contract taken straight from questions.MD:
  ("valid", d)     transcript is well nested and fully closed; d = max depth
  ("invalid", i)   i = index of the FIRST close event that cannot be matched
  "incomplete"     every close matched, but something is still open at the end

Rule 2 only gets checked once the whole transcript has been read, so an
unmatchable close always wins over an unclosed component.
"""
from harness import case

ENTRY_POINT = "check_transcript"


def _balanced(depth):
    """open 1..depth, then close depth..1  ->  ("valid", depth)"""
    return ([("open", k) for k in range(1, depth + 1)]
            + [("close", k) for k in range(depth, 0, -1)])


def _sequential(count):
    """open/close count components side by side  ->  ("valid", 1)"""
    return [event for k in range(count)
            for event in (("open", k), ("close", k))]


# Used only by the complexity measurement on the results window, once every
# testcase passes. Hand it a size, get back a valid transcript of n events.
SCALING_SIZES = [2000, 4000, 8000, 16000, 32000]


def scaling_input(n):
    return {"events": _balanced(n // 2)}


TEST_CASES = [

    # ----------------------------------------------------------------
    # The four worked examples in the question
    # ----------------------------------------------------------------

    case(
        "Example 1 - valid nested transcript",
        expected=("valid", 2),
        events=[
            ("open", 7),
            ("open", 3),
            ("close", 3),
            ("open", 9),
            ("close", 9),
            ("close", 7),
        ],
    ),

    case(
        "Example 2 - close out of order",
        expected=("invalid", 2),
        events=[
            ("open", 7),
            ("open", 3),
            ("close", 7),
            ("close", 3),
        ],
    ),

    case(
        "Example 3 - component left open",
        expected="incomplete",
        events=[
            ("open", 7),
            ("open", 3),
            ("close", 3),
        ],
    ),

    case(
        "Example 4 - empty transcript",
        expected=("valid", 0),
        events=[],
    ),

    # ----------------------------------------------------------------
    # Depth arithmetic - d is the MAXIMUM depth, not the final or the
    # component count
    # ----------------------------------------------------------------

    case(
        "Single component has depth 1",
        expected=("valid", 1),
        events=[("open", 1), ("close", 1)],
    ),

    case(
        "Five components nested straight down",
        expected=("valid", 5),
        events=_balanced(5),
    ),

    case(
        "Six components side by side still have depth 1",
        expected=("valid", 1),
        events=[
            ("open", 1), ("close", 1),
            ("open", 2), ("close", 2),
            ("open", 3), ("close", 3),
        ],
    ),

    case(
        "Nested pair, then a separate component",
        expected=("valid", 2),
        events=[
            ("open", 1),
            ("open", 2),
            ("close", 2),
            ("close", 1),
            ("open", 3),
            ("close", 3),
        ],
    ),

    case(
        "Depth returns to zero before the end",
        expected=("valid", 4),
        events=[
            ("open", 10), ("open", 20), ("open", 30), ("open", 40),
            ("close", 40), ("close", 30), ("close", 20), ("close", 10),
        ],
    ),

    case(
        "Deepest nesting happens last",
        expected=("valid", 3),
        events=[
            ("open", 1), ("open", 2), ("close", 2), ("close", 1),
            ("open", 3), ("open", 4), ("open", 5),
            ("close", 5), ("close", 4), ("close", 3),
        ],
    ),

    case(
        "Deepest nesting happens first",
        expected=("valid", 3),
        events=[
            ("open", 1), ("open", 2), ("open", 3),
            ("close", 3), ("close", 2), ("close", 1),
            ("open", 4), ("close", 4),
        ],
    ),

    case(
        "Sibling subtrees of unequal depth",
        expected=("valid", 3),
        events=[
            ("open", 1),
            ("open", 2), ("open", 3), ("close", 3), ("close", 2),
            ("open", 4), ("close", 4),
            ("close", 1),
        ],
    ),

    case(
        "Identifiers are arbitrary, not positions",
        expected=("valid", 2),
        events=[
            ("open", 1000000),
            ("open", 0),
            ("close", 0),
            ("close", 1000000),
        ],
    ),

    # ----------------------------------------------------------------
    # Rule 1 - the index of the FIRST unmatchable close
    # ----------------------------------------------------------------

    case(
        "Close with nothing open at index 0",
        expected=("invalid", 0),
        events=[("close", 1)],
    ),

    case(
        "Close names a component that is not on top",
        expected=("invalid", 2),
        events=[("open", 1), ("open", 2), ("close", 1)],
    ),

    case(
        "Close names a component that was never opened",
        expected=("invalid", 1),
        events=[("open", 1), ("close", 2)],
    ),

    case(
        "First close is fine, a later one is not",
        expected=("invalid", 4),
        events=[
            ("open", 1), ("close", 1),
            ("open", 2), ("open", 3), ("close", 2),
        ],
    ),

    case(
        "Bad close part way down a nest",
        expected=("invalid", 3),
        events=[("open", 1), ("open", 2), ("open", 3), ("close", 2)],
    ),

    case(
        "Close on an empty stack part way through",
        expected=("invalid", 2),
        events=[("open", 1), ("close", 1), ("close", 2)],
    ),

    case(
        "Stray close after a fully balanced block",
        expected=("invalid", 4),
        events=[
            ("open", 1), ("open", 2), ("close", 2), ("close", 1),
            ("close", 3),
        ],
    ),

    case(
        "Unmatchable close outranks a component left open",
        expected=("invalid", 2),
        events=[("open", 1), ("open", 2), ("close", 1), ("open", 3)],
    ),

    # ----------------------------------------------------------------
    # Rule 2 - every close matched, but the transcript ends mid-flight
    # ----------------------------------------------------------------

    case(
        "One component, never closed",
        expected="incomplete",
        events=[("open", 42)],
    ),

    case(
        "Four components, none closed",
        expected="incomplete",
        events=[("open", 1), ("open", 2), ("open", 3), ("open", 4)],
    ),

    case(
        "Ends on a correct close but the outer one is still open",
        expected="incomplete",
        events=[
            ("open", 1),
            ("open", 2), ("close", 2),
            ("open", 3), ("close", 3),
        ],
    ),

    # ----------------------------------------------------------------
    # Scale - O(n) with a stack should stroll through these
    # ----------------------------------------------------------------

    case(
        "Stress - nested 1000 deep",
        expected=("valid", 1000),
        events=_balanced(1000),
    ),

    case(
        "Stress - 5000 components side by side",
        expected=("valid", 1),
        events=_sequential(5000),
    ),
]
