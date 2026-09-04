"""Renders a Submission in LeetCode's submission-result format."""
from __future__ import annotations

import textwrap
from typing import List, Optional

from . import theme as T
from .runner import (ACCEPTED, COMPILE_ERROR, HARNESS_ERROR, RUNTIME_ERROR,
                     TIME_LIMIT, WRONG_ANSWER, CaseResult, Submission)

VERDICT_STYLE = {
    ACCEPTED: (T.GREEN, T.TICK),
    WRONG_ANSWER: (T.RED, T.CROSS),
    RUNTIME_ERROR: (T.RED, T.CROSS),
    COMPILE_ERROR: (T.RED, T.CROSS),
    TIME_LIMIT: (T.YELLOW, T.CROSS),
    HARNESS_ERROR: (T.YELLOW, "!"),
}

INDENT = "  "


def _out(line: str = "") -> None:
    print(line)


def _section(label: str) -> None:
    _out(INDENT + T.paint(label, T.MUTED))


def _value(text: str, style: str = T.WHITE) -> None:
    limit = T.width() - 6
    for line in text.splitlines() or [""]:
        chunks = textwrap.wrap(
            line, limit, subsequent_indent="    ", break_on_hyphens=False,
        ) or [""]
        for chunk in chunks:
            _out(INDENT * 2 + T.paint(chunk, style))


def _fmt_runtime(ms: float) -> str:
    if ms < 1:
        return f"{ms:.2f} ms"
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s"


def header(sub: Submission) -> None:
    _out()
    _out(INDENT + T.paint(sub.problem.slug, T.BOLD, T.WHITE)
         + T.paint(f"  {T.DOT}  {sub.problem.title}", T.MUTED))
    _out(T.rule())
    _out()

    colour, glyph = VERDICT_STYLE.get(sub.verdict, (T.YELLOW, "?"))
    _out(INDENT + T.paint(f"{glyph} {sub.verdict}", T.BOLD, colour))

    if sub.total:
        tally = f"{sub.passed} / {sub.total} testcases passed"
        _out(INDENT + T.paint(tally, colour if not sub.accepted else T.MUTED))
        stats = [f"Runtime {_fmt_runtime(sub.runtime_ms)}"]
        if sub.peak_kb is not None:
            stats.append(f"Memory {sub.peak_kb / 1024:.2f} MB")
        _out(INDENT + T.paint("  ".join(stats), T.MUTED))
    _out()


def case_list(sub: Submission) -> None:
    if not sub.cases:
        return
    width = T.width()
    number_w = len(str(sub.total))
    name_w = max(20, width - number_w - 22)
    for case_result in sub.cases:
        if case_result.ok:
            glyph, colour = T.TICK, T.GREEN
            note = _fmt_runtime(case_result.runtime_ms)
            note_style = T.MUTED
        elif case_result.status == "error":
            glyph, colour = T.CROSS, T.RED
            note = (case_result.error or {}).get("type", "Error")
            note_style = T.RED
        else:
            glyph, colour = T.CROSS, T.RED
            note = "Wrong Answer"
            note_style = T.RED
        name = case_result.name
        if len(name) > name_w:
            # leave one column of air before the timing/verdict column
            name = name[: name_w - len(T.ELLIPSIS) - 1] + T.ELLIPSIS
        _out(
            INDENT
            + T.paint(glyph, colour)
            + T.paint(f" Case {case_result.number:>{number_w}}  ", T.MUTED)
            + T.paint(name.ljust(name_w), T.WHITE if not case_result.ok else T.MUTED)
            + T.paint(note, note_style)
        )
    _out()


def failure_panel(sub: Submission, case_result: CaseResult) -> None:
    _out(T.rule())
    _out(INDENT + T.paint(f"Case {case_result.number}", T.BOLD, T.WHITE)
         + T.paint(f"  {T.DOT}  {case_result.name}", T.MUTED))
    _out()

    _section("Input")
    if case_result.args_repr:
        for key, value in case_result.args_repr.items():
            _value(f"{key} = {value}")
    else:
        _value("(no arguments)")
    _out()

    if case_result.stdout.strip():
        _section("Stdout")
        _value(case_result.stdout.rstrip(), T.MUTED)
        _out()

    _section("Output")
    if case_result.status == "error":
        error = case_result.error or {}
        _value(f"{error.get('type')}: {error.get('message')}", T.RED)
        if error.get("line"):
            where = f"Line {error['line']} in {error.get('func') or '<module>'} ({error.get('file')})"
            _out(INDENT * 2 + T.paint(where, T.MUTED))
            if error.get("code"):
                _out(INDENT * 3 + T.paint(error["code"], T.MUTED))
    else:
        _value(case_result.output_repr or "None", T.RED)
    _out()

    _section("Expected")
    _value(case_result.expected_repr, T.GREEN)
    _out()


def load_error_panel(sub: Submission) -> None:
    error = sub.load_error or {}
    _out(T.rule())
    origin = {
        "solution": "solution.py",
        "tests": "tests.py",
        "harness": "the harness",
    }.get(error.get("phase"), "your code")
    if sub.verdict == TIME_LIMIT:
        _out(INDENT + T.paint("Execution stopped", T.BOLD, T.WHITE))
        _out()
        _value(error.get("message", ""), T.YELLOW)
        _out()
        return
    _out(INDENT + T.paint(f"Raised while loading {origin}", T.BOLD, T.WHITE))
    _out()
    _value(f"{error.get('type')}: {error.get('message')}", T.RED)
    if error.get("line"):
        where = f"Line {error['line']} in {error.get('func') or '<module>'} ({error.get('file')})"
        _out(INDENT * 2 + T.paint(where, T.MUTED))
        if error.get("code"):
            _out(INDENT * 3 + T.paint(error["code"], T.MUTED))
    _out()


def footer(sub: Submission, shown: int, hidden: int) -> None:
    _out(T.rule())
    if sub.accepted:
        _out(INDENT + T.paint(
            f"{T.TICK} All {sub.total} testcases passed. Nice.", T.GREEN))
    elif hidden:
        _out(INDENT + T.paint(
            f"{hidden} more failing testcase(s) hidden {T.DOT} press 'a' or run with --all",
            T.MUTED))
    _out()


def submission(sub: Submission, show_all: bool = False,
               show_cases: bool = True) -> None:
    header(sub)
    if sub.load_error and not sub.cases:
        load_error_panel(sub)
        footer(sub, 0, 0)
        return
    if show_cases:
        case_list(sub)
    failures: List[CaseResult] = sub.failures
    to_show = failures if show_all else failures[:1]
    for case_result in to_show:
        failure_panel(sub, case_result)
    footer(sub, len(to_show), len(failures) - len(to_show))


def compact_status(sub: Optional[Submission]) -> str:
    """One-cell status used by the problem menu."""
    if sub is None:
        return T.paint("not run", T.MUTED)
    colour, glyph = VERDICT_STYLE.get(sub.verdict, (T.YELLOW, "?"))
    if sub.total:
        return T.paint(f"{glyph} {sub.passed}/{sub.total}", colour)
    return T.paint(f"{glyph} {sub.verdict}", colour)
