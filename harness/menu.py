"""Interactive terminal front end."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

from . import render, scaffold
from . import theme as T
from .discovery import Problem, discover
from .runner import DEFAULT_TIMEOUT, Submission, submit

LAST: Dict[str, Submission] = {}


def banner() -> None:
    T.clear_screen()
    print()
    print("  " + T.paint("DSA PRACTICE", T.BOLD, T.GREEN)
          + T.paint(f"   {T.DOT}   local judge, LeetCode format", T.MUTED))
    print(T.rule())


def problem_table(problems: List[Problem]) -> None:
    print()
    if not problems:
        print("  " + T.paint("No problems yet.", T.MUTED))
        print("  " + T.paint("Press 'n' to create your first one.", T.MUTED))
        print()
        return
    print("  " + T.paint("#".rjust(3) + "  " + "PROBLEM".ljust(34) + "STATUS", T.MUTED))
    for i, problem in enumerate(problems, 1):
        status = render.compact_status(LAST.get(problem.slug))
        print("  " + T.paint(f"{i:>3}", T.BOLD, T.WHITE)
              + "  " + T.paint(problem.slug.ljust(34), T.WHITE) + status)
    print()


def prompt(options: str) -> str:
    print(T.rule())
    print("  " + T.paint(options, T.MUTED))
    try:
        return input("  " + T.paint(f"{T.ARROW} ", T.GREEN)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


def show_question(problem: Problem) -> None:
    T.clear_screen()
    path = problem.question
    print()
    print("  " + T.paint(problem.slug, T.BOLD, T.WHITE))
    print(T.rule())
    print()
    if path is None:
        print("  " + T.paint("No question file in this folder.", T.MUTED))
    else:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            print("  " + line)
    print()
    prompt("enter  back")


def run_once(problem: Problem, show_all: bool = False, clear: bool = True,
             timeout: float = DEFAULT_TIMEOUT) -> Submission:
    if clear:
        T.clear_screen()
    print()
    print("  " + T.paint(f"Judging {problem.slug} ...", T.MUTED))
    result = submit(problem, timeout=timeout)
    LAST[problem.slug] = result
    if clear:
        T.clear_screen()
    render.submission(result, show_all=show_all)
    return result


def watch(problem: Problem, show_all: bool = False,
          timeout: float = DEFAULT_TIMEOUT) -> None:
    """Re-judge whenever solution.py or tests.py changes on disk."""
    def stamp() -> float:
        return max((p.stat().st_mtime for p in problem.watched_files()), default=0.0)

    last = -1.0
    print()
    try:
        while True:
            current = stamp()
            if current != last:
                last = current
                run_once(problem, show_all=show_all, timeout=timeout)
                print("  " + T.paint(
                    f"Watching {problem.slug}/  {T.DOT}  save to re-run  {T.DOT}  Ctrl-C to stop",
                    T.MUTED))
                print()
            time.sleep(0.4)
    except KeyboardInterrupt:
        print()
        print("  " + T.paint("Stopped watching.", T.MUTED))
        print()


def problem_screen(problem: Problem) -> None:
    show_all = False
    run_once(problem, show_all=show_all)
    while True:
        choice = prompt("enter re-run   g browser   a all failures   "
                        "d description   w watch   b back   q quit").lower()
        if choice in ("q", "quit", "exit"):
            raise SystemExit(0)
        if choice in ("b", "back"):
            return
        if choice in ("d", "desc", "description"):
            show_question(problem)
            run_once(problem, show_all=show_all)
            continue
        if choice in ("g", "gui", "window", "browser"):
            from . import web
            web.launch(focus_slug=problem.slug, timeout=DEFAULT_TIMEOUT, auto_run=True)
            run_once(problem, show_all=show_all)
            continue
        if choice in ("a", "all"):
            show_all = not show_all
            T.clear_screen()
            render.submission(LAST[problem.slug], show_all=show_all)
            continue
        if choice in ("w", "watch"):
            watch(problem, show_all=show_all)
            run_once(problem, show_all=show_all)
            continue
        run_once(problem, show_all=show_all)


def new_problem() -> None:
    print()
    try:
        name = input("  " + T.paint("New problem name (e.g. two sum): ", T.WHITE)).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not name:
        return
    try:
        target = scaffold.create(name)
    except (FileExistsError, FileNotFoundError) as exc:
        print()
        print("  " + T.paint(f"{T.CROSS} {exc}", T.RED))
        print()
        prompt("enter  back")
        return
    scaffold.announce(target)
    prompt("enter  back")


def loop() -> None:
    while True:
        problems = discover()
        banner()
        problem_table(problems)
        options = "number run   n new problem   w web dashboard   r refresh   q quit"
        choice = prompt(options).lower()
        if choice in ("q", "quit", "exit"):
            print()
            return
        if choice in ("n", "new"):
            new_problem()
            continue
        if choice in ("w", "web"):
            from . import web
            web.launch()
            continue
        if choice in ("r", "refresh", ""):
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(problems):
            problem_screen(problems[int(choice) - 1])
            continue
        matches = [p for p in problems if choice in p.slug.lower()]
        if len(matches) == 1:
            problem_screen(matches[0])
