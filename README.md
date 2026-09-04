# DSA Practice

A local judge for COMP2123 practice problems. Runs your solution against a set
of testcases and reports the result in LeetCode's submission format.

## Run it

Three ways, pick whichever is closest to hand.

**In VSCode** - with any file of the problem open, press `Ctrl+Shift+B`. That
judges the problem the open file belongs to and shows the results in a window.
Terminal -> Run Task has the other two: *(terminal)* and *(watch)*.

> Needs `Code Practice` open as your workspace folder, since that is where
> `.vscode/` lives. If you open a folder above it instead, move `.vscode/` into
> that folder - the tasks resolve everything from the open file, so they keep
> working unchanged.

**From inside a problem folder:**

```
cd nested_transcript
python judge.py         # judge once, in the terminal
python judge.py -g      # judge once, in a pop-up window
python judge.py -w      # re-judge every time you hit save
python judge.py -a      # a detail panel for every failure
```

## The results window

`-g` / `--gui` puts the same result in a scrollable window instead of the
terminal. `F5` re-runs, `Esc` closes, *Copy report* puts the whole thing on the
clipboard as plain text.

- **Not accepted** - every failing case is listed, then laid out in full:
  Input, Stdout, your Output, and Expected. All of them, in one scroll.
- **Accepted** - runtime and peak memory, a per-testcase runtime bar chart, and
  a measured complexity panel.

That complexity panel runs your solution at five input sizes, fits the results
against the usual growth curves, and names the closest one for both time and
space, with the raw numbers underneath. It is measured from your own runs on
this machine. LeetCode's "beats 88% of submissions" compares you against other
people; there is no submission population here, so that number would be
invented, and this shows you real scaling instead.

It needs to know how to build an input of size n, so it only appears if the
problem's `tests.py` defines one:

```python
SCALING_SIZES = [2000, 4000, 8000, 16000, 32000]

def scaling_input(n):
    return {"events": _balanced(n // 2)}
```

Without it the window still shows runtime and memory, just not the scaling.

**From this folder:**

```
python practice.py                      # interactive menu
python practice.py nested_transcript    # judge one problem and exit
python practice.py nested_transcript -w # re-judge every time you hit save
python practice.py nested_transcript -a # a detail panel for every failure
python practice.py list                 # what problems exist
python practice.py new "two sum"        # scaffold a new problem folder
```

The problem argument takes a name or any path pointing into the folder, so
tab-completion (`nested_transcript/`), `.`, and full paths all work.

Exit code is `0` on Accepted, `1` otherwise, so it drops into a shell loop or a
pre-commit hook if you ever want that.

Inside the menu: a number runs that problem, then `enter` re-runs, `a` toggles
all failure panels, `d` shows the question, `w` watches for saves, `b` goes
back, `q` quits.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `Accepted` | every testcase passed |
| `Wrong Answer` | ran fine, returned the wrong value |
| `Runtime Error` | raised an exception - shows the file, line and source |
| `Compile Error` | `solution.py` does not parse |
| `Time Limit Exceeded` | ran past `--timeout` seconds (default 10) |
| `Harness Error` | your `tests.py` is broken, not your solution |

As on LeetCode, the **first** failing testcase decides the verdict, and only
that case gets a detail panel unless you pass `-a`.

## Layout

```
Code Practice/
  practice.py            the command you run
  pytest.ini             lets pytest run from here across every problem
  .vscode/tasks.json     the Ctrl+Shift+B binding
  harness/               the judge - you never need to edit this
  _template/             what `practice.py new` copies
  nested_transcript/     one problem
    questions.MD           the problem statement
    solution.py            your code
    tests.py               the testcases
    judge.py               judges this problem, run from in here
    test_algorithm.py      pytest adapter over the same testcases
    conftest.py            import paths for pytest
```

Any folder here containing a `solution.py` is picked up as a problem. Add as
many as you like; `harness/` and `_template/` are skipped.

## Adding a problem

```
python practice.py new "two sum"
```

Then fill in three files:

**`question.md`** - paste the problem statement.

**`solution.py`** - write the function.

**`tests.py`** - point `ENTRY_POINT` at your function and list the cases. Every
keyword other than `expected` becomes an argument, passed in the order you
write it:

```python
from harness import case

ENTRY_POINT = "two_sum"

TEST_CASES = [
    case("Example 1", expected=[0, 1], nums=[2, 7, 11, 15], target=9),
    case("Duplicates", expected=[0, 1], nums=[3, 3], target=6),
]
```

That calls `two_sum([2, 7, 11, 15], 9)` and compares the result to `[0, 1]`.
The argument names are what show up in the **Input** panel, so name them the
way the question does.

If a problem accepts more than one right answer, hand the case a `checker`.
It is called as `checker(actual, expected)` and just has to return truthy:

```python
NUMS = [2, 7, 11, 15]

case(
    "Any pair that sums to the target",
    expected=9,
    checker=lambda actual, target: sum(NUMS[i] for i in actual) == target,
    nums=NUMS,
)
```

## pytest

Every problem also works as a normal pytest suite over the exact same cases:

```
cd nested_transcript
python -m pytest test_algorithm.py -q     # one problem
```

or every problem at once, from the practice root:

```
python -m pytest -q
```

`test_algorithm.py` and `conftest.py` are generated - there is nothing to edit
in them. Add testcases in `tests.py` and both the judge and pytest pick them up.

## Notes

- Each solution runs in a child process, so an infinite loop or a hard crash
  shows up as a verdict instead of taking the terminal down with it.
- Arguments are deep-copied per case, so a solution that mutates its input
  cannot poison a later testcase.
- Anything your solution `print`s is captured and shown in a **Stdout** panel,
  the way LeetCode does it. Debug prints are safe to leave in.
