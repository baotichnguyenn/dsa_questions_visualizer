#!/usr/bin/env python3
"""DSA practice judge - LeetCode-style results, in a window or in the terminal.

    python practice.py                     interactive menu
    python practice.py nested_transcript   judge one problem
    python practice.py nested_transcript -g  results in a pop-up window
    python practice.py nested_transcript -w  re-judge on every save
    python practice.py list                list problems
    python practice.py new "two sum"       scaffold a new problem folder
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Before importing harness: theme.py picks its glyphs from the stream
# encoding at import time, and Windows pipes default to cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import menu, render, scaffold  # noqa: E402
from harness import theme as T  # noqa: E402
from harness.discovery import discover, find  # noqa: E402
from harness.runner import DEFAULT_TIMEOUT  # noqa: E402


def cmd_list() -> int:
    problems = discover()
    print()
    if not problems:
        print("  " + T.paint("No problems found.", T.MUTED))
        print("  " + T.paint('Create one with:  python practice.py new "two sum"', T.MUTED))
        print()
        return 0
    for problem in problems:
        tests = problem.tests
        note = "ready" if tests else "missing tests.py"
        style = T.MUTED if tests else T.YELLOW
        print("  " + T.paint(problem.slug.ljust(34), T.WHITE) + T.paint(note, style))
    print()
    return 0


def cmd_new(name: str) -> int:
    try:
        target = scaffold.create(name)
    except (FileExistsError, FileNotFoundError) as exc:
        print()
        print("  " + T.paint(f"{T.CROSS} {exc}", T.RED))
        print()
        return 1
    scaffold.announce(target)
    return 0


def cmd_run(slug: str, args: argparse.Namespace) -> int:
    problem = find(slug)
    if problem is None:
        print()
        print("  " + T.paint(f"{T.CROSS} No problem matching '{slug}'.", T.RED))
        print("  " + T.paint("Known problems: "
                             + (", ".join(p.slug for p in discover()) or "none"), T.MUTED))
        print()
        return 2
    if args.gui:
        from harness import gui
        return gui.launch(problem, timeout=args.timeout)
    if args.watch:
        menu.watch(problem, show_all=args.all, timeout=args.timeout)
        return 0
    result = menu.run_once(problem, show_all=args.all, clear=not args.plain,
                           timeout=args.timeout)
    return 0 if result.accepted else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="practice",
        description="Judge your DSA solutions locally, LeetCode style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("target", nargs="?",
                        help="problem folder, or 'list' / 'new'")
    parser.add_argument("name", nargs="?", help="name for 'new'")
    parser.add_argument("-g", "--gui", action="store_true",
                        help="show the results in a pop-up window instead")
    parser.add_argument("-a", "--all", action="store_true",
                        help="show a detail panel for every failing case")
    parser.add_argument("-w", "--watch", action="store_true",
                        help="re-judge whenever solution.py or tests.py is saved")
    parser.add_argument("--plain", action="store_true",
                        help="do not clear the screen (good for piping)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"seconds before Time Limit Exceeded (default {DEFAULT_TIMEOUT:g})")
    args = parser.parse_args(argv)

    if args.target is None:
        menu.loop()
        return 0
    if args.target == "list":
        return cmd_list()
    if args.target == "new":
        if not args.name:
            print()
            print("  " + T.paint('Usage: python practice.py new "two sum"', T.MUTED))
            print()
            return 2
        return cmd_new(args.name)
    return cmd_run(args.target, args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        raise SystemExit(130)
