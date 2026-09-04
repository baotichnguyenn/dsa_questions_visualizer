"""A results window, in LeetCode's shape, drawn with tkinter.

Same Submission the terminal renderer uses - this is just a second front end.
Accepted gets the runtime and space analysis; anything else gets every failing
case, in full, in one scrollable column.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Any, Dict, List, Optional

from .discovery import Problem
from .runner import (ACCEPTED, COMPILE_ERROR, HARNESS_ERROR, RUNTIME_ERROR,
                     TIME_LIMIT, WRONG_ANSWER, CaseResult, Submission, submit)

BG = "#1a1a1a"
PANEL = "#262626"
INSET = "#1e1e1e"
BORDER = "#3a3a3a"
FG = "#e6e6e6"
MUTED = "#8a8a8a"
GREEN = "#00b8a3"
RED = "#ef4743"
YELLOW = "#ffa116"

VERDICT_COLOR = {
    ACCEPTED: GREEN,
    WRONG_ANSWER: RED,
    RUNTIME_ERROR: RED,
    COMPILE_ERROR: RED,
    TIME_LIMIT: YELLOW,
    HARNESS_ERROR: YELLOW,
}

PAD = 18


def _fmt_ms(ms: float) -> str:
    if ms < 1:
        return f"{ms:.2f} ms"
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s"


def _fmt_kb(kb: float) -> str:
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb / 1024:.2f} MB"


class ResultsWindow:
    def __init__(self, problem: Problem, timeout: float = 10.0,
                 with_scaling: bool = True) -> None:
        self.problem = problem
        self.timeout = timeout
        self.with_scaling = with_scaling
        self.submission: Optional[Submission] = None
        self._busy = False
        self._user_scrolled = False

        self.root = tk.Tk()
        self.root.title(f"{problem.slug} - judging...")
        self.root.configure(bg=BG)
        self.root.minsize(680, 460)
        self._centre(1060, 800)
        self._raise()

        self.ui = tkfont.Font(family="Segoe UI", size=10)
        self.ui_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.small = tkfont.Font(family="Segoe UI", size=9)
        self.h1 = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.h2 = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.mono = tkfont.Font(family="Consolas", size=10)
        self.mono_small = tkfont.Font(family="Consolas", size=9)

        self._build_chrome()
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("<F5>", lambda _e: self.rerun())
        self.root.bind("<Control-r>", lambda _e: self.rerun())

    def _centre(self, want_w: int, want_h: int) -> None:
        """Fit inside the screen, then centre. Display scaling can make the
        requested size larger than the desktop, which parks it off-screen."""
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(want_w, screen_w - 80)
        height = min(want_h, screen_h - 120)
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _raise(self) -> None:
        """Come to the front without staying pinned there."""
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    # ---------------------------------------------------------------- chrome

    def _build_chrome(self) -> None:
        self.header = tk.Frame(self.root, bg=PANEL)
        self.header.pack(fill="x", side="top")

        inner = tk.Frame(self.header, bg=PANEL)
        inner.pack(fill="x", padx=PAD, pady=(14, 14))

        left = tk.Frame(inner, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)

        self.verdict_label = tk.Label(left, text="Judging...", font=self.h1,
                                      bg=PANEL, fg=MUTED, anchor="w")
        self.verdict_label.pack(anchor="w")

        self.tally_label = tk.Label(left, text=self.problem.slug, font=self.ui,
                                    bg=PANEL, fg=MUTED, anchor="w")
        self.tally_label.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(inner, bg=PANEL)
        right.pack(side="right")

        self.rerun_button = self._button(right, "Re-run  (F5)", self.rerun)
        self.rerun_button.pack(side="left", padx=(0, 8))
        self._button(right, "Copy report", self.copy_report).pack(side="left")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # Scrollable body: a canvas holding one frame that we rebuild per run.
        holder = tk.Frame(self.root, bg=BG)
        holder.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(holder, bg=BG, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(holder, orient="vertical",
                                      command=self.canvas.yview,
                                      bg=PANEL, troughcolor=BG, bd=0,
                                      highlightthickness=0,
                                      activebackground=MUTED)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(self.canvas, bg=BG)
        self.body_id = self.canvas.create_window((0, 0), window=self.body,
                                                 anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_wheel()

    def _button(self, parent, text, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command, font=self.ui,
                         bg=INSET, fg=FG, activebackground=BORDER,
                         activeforeground=FG, relief="flat", bd=0,
                         padx=14, pady=6, cursor="hand2",
                         highlightthickness=1, highlightbackground=BORDER)

    def _on_body_configure(self, _event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfig(self.body_id, width=event.width)
        self._wrap = max(360, event.width - 2 * PAD - 40)

    def _over_canvas(self, x_root: int, y_root: int) -> bool:
        """Is the pointer actually inside our scroll area?

        bind_all sees every wheel event the application gets, including ones
        aimed elsewhere, so the handler has to check for itself.
        """
        widget = self.root.winfo_containing(x_root, y_root)
        while widget is not None:
            if widget is self.canvas:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _scroll(self, units: int, x_root: int, y_root: int) -> None:
        if not self._over_canvas(x_root, y_root):
            return
        region = self.canvas.bbox("all")
        if region is None or region[3] - region[1] <= self.canvas.winfo_height():
            return
        self._user_scrolled = True
        self.canvas.yview_scroll(units, "units")

    def _bind_wheel(self) -> None:
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._scroll(int(-e.delta / 120), e.x_root, e.y_root))
        self.canvas.bind_all(
            "<Button-4>", lambda e: self._scroll(-1, e.x_root, e.y_root))
        self.canvas.bind_all(
            "<Button-5>", lambda e: self._scroll(1, e.x_root, e.y_root))

    def _pin_to_top(self, remaining: int = 8) -> None:
        """Hold the view at the top until the reader scrolls for themselves.

        Content keeps growing for a few frames after a run finishes, and a
        stray wheel event in that window would otherwise leave the reader
        somewhere in the middle of the results.
        """
        if self._user_scrolled or remaining <= 0:
            return
        self.canvas.yview_moveto(0)
        self.root.after(60, lambda: self._pin_to_top(remaining - 1))

    # ------------------------------------------------------------- building

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def _card(self, parent=None, pady=(0, 12)) -> tk.Frame:
        holder = tk.Frame(parent or self.body, bg=BORDER)
        holder.pack(fill="x", padx=PAD, pady=pady)
        inner = tk.Frame(holder, bg=PANEL)
        inner.pack(fill="both", padx=1, pady=1)
        return inner

    def _label(self, parent, text, font=None, fg=FG, bg=PANEL, **kwargs):
        return tk.Label(parent, text=text, font=font or self.ui, bg=bg, fg=fg,
                        anchor="w", justify="left", **kwargs)

    def _field(self, parent, title: str, value: str, value_color=FG) -> None:
        self._label(parent, title, font=self.small, fg=MUTED).pack(
            anchor="w", padx=14, pady=(10, 2))
        self._label(parent, value, font=self.mono, fg=value_color,
                    wraplength=getattr(self, "_wrap", 900)).pack(
            anchor="w", padx=14, pady=(0, 4), fill="x")

    # -------------------------------------------------------------- running

    def rerun(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.rerun_button.configure(state="disabled", text="Judging...")
        self.verdict_label.configure(text="Judging...", fg=MUTED)
        self.tally_label.configure(text=f"{self.problem.slug}  -  running testcases")
        self._clear_body()
        self.root.title(f"{self.problem.slug} - judging...")

        def work():
            try:
                result = submit(self.problem, timeout=self.timeout,
                                with_scaling=self.with_scaling)
            except BaseException as exc:  # keep the window alive no matter what
                self.root.after(0, self._failed_to_run, exc)
                return
            self.root.after(0, self._present, result)

        threading.Thread(target=work, daemon=True).start()

    def _failed_to_run(self, exc: BaseException) -> None:
        self._busy = False
        self.rerun_button.configure(state="normal", text="Re-run  (F5)")
        self.verdict_label.configure(text="Harness Error", fg=YELLOW)
        self.tally_label.configure(text=f"{type(exc).__name__}: {exc}")

    def _present(self, sub: Submission) -> None:
        self.submission = sub
        self._busy = False
        self.rerun_button.configure(state="normal", text="Re-run  (F5)")

        color = VERDICT_COLOR.get(sub.verdict, YELLOW)
        glyph = "✓" if sub.accepted else "✗"
        self.verdict_label.configure(text=f"{glyph} {sub.verdict}", fg=color)
        self.root.title(f"{self.problem.slug} - {sub.verdict}")

        if sub.total:
            tally = f"{sub.passed} / {sub.total} testcases passed"
        else:
            tally = self.problem.slug
        self.tally_label.configure(text=tally,
                                   fg=MUTED if sub.accepted else color)

        self._clear_body()
        tk.Frame(self.body, bg=BG, height=PAD - 6).pack()

        if sub.load_error and not sub.cases:
            self._section_load_error(sub)
        elif sub.accepted:
            self._section_analysis(sub)
            self._section_case_list(sub)
        else:
            self._section_case_list(sub)
            self._section_failures(sub)

        tk.Frame(self.body, bg=BG, height=PAD).pack()
        self._user_scrolled = False
        self._pin_to_top()

    # ------------------------------------------------------------- sections

    def _section_load_error(self, sub: Submission) -> None:
        error = sub.load_error or {}
        card = self._card()
        origin = {"solution": "solution.py", "tests": "tests.py",
                  "harness": "the harness"}.get(error.get("phase"), "your code")
        title = ("Execution stopped" if sub.verdict == TIME_LIMIT
                 else f"Raised while loading {origin}")
        self._label(card, title, font=self.h2).pack(anchor="w", padx=14, pady=(12, 0))
        message = error.get("message", "")
        if sub.verdict != TIME_LIMIT:
            message = f"{error.get('type')}: {message}"
        self._label(card, message, font=self.mono, fg=RED,
                    wraplength=getattr(self, "_wrap", 900)).pack(
            anchor="w", padx=14, pady=(8, 4), fill="x")
        if error.get("line"):
            where = (f"Line {error['line']} in {error.get('func') or '<module>'}"
                     f" ({error.get('file')})")
            self._label(card, where, font=self.small, fg=MUTED).pack(
                anchor="w", padx=14)
            if error.get("code"):
                self._label(card, error["code"], font=self.mono_small,
                            fg=MUTED).pack(anchor="w", padx=28, pady=(2, 0))
        tk.Frame(card, bg=PANEL, height=12).pack()

    def _stat_tile(self, parent, title: str, value: str, note: str) -> None:
        tile = tk.Frame(parent, bg=INSET)
        tile.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self._label(tile, title, font=self.small, fg=MUTED, bg=INSET).pack(
            anchor="w", padx=14, pady=(12, 0))
        self._label(tile, value, font=self.h2, fg=GREEN, bg=INSET).pack(
            anchor="w", padx=14, pady=(2, 0))
        self._label(tile, note, font=self.small, fg=MUTED, bg=INSET).pack(
            anchor="w", padx=14, pady=(2, 12))

    def _section_analysis(self, sub: Submission) -> None:
        card = self._card()
        self._label(card, "Runtime and space", font=self.h2).pack(
            anchor="w", padx=14, pady=(12, 0))

        tiles = tk.Frame(card, bg=PANEL)
        tiles.pack(fill="x", padx=8, pady=(6, 0))
        slowest = max((c.runtime_ms for c in sub.cases), default=0.0)
        self._stat_tile(tiles, "Runtime", _fmt_ms(sub.runtime_ms),
                        f"{sub.total} testcases, slowest {_fmt_ms(slowest)}")
        self._stat_tile(tiles, "Memory", _fmt_kb(sub.peak_kb or 0.0),
                        "peak tracked allocation")

        self._label(card, "Per-testcase runtime", font=self.small,
                    fg=MUTED).pack(anchor="w", padx=14, pady=(10, 4))
        self._runtime_chart(card, sub)

        self._scaling_block(card, sub)
        tk.Frame(card, bg=PANEL, height=12).pack()

    def _runtime_chart(self, parent, sub: Submission) -> None:
        rows = sub.cases
        height = 22 + len(rows) * 14
        chart = tk.Canvas(parent, bg=INSET, height=height,
                          highlightthickness=0, bd=0)
        chart.pack(fill="x", padx=14, pady=(0, 6))

        peak = max((c.runtime_ms for c in rows), default=0.0) or 1.0

        def draw(_event=None):
            chart.delete("all")
            usable = max(120, chart.winfo_width() - 130)
            for i, case_result in enumerate(rows):
                y = 12 + i * 14
                chart.create_text(8, y, anchor="w", text=f"{case_result.number}",
                                  fill=MUTED, font=self.mono_small)
                length = max(1, int(usable * (case_result.runtime_ms / peak)))
                chart.create_rectangle(34, y - 4, 34 + length, y + 4,
                                       fill=GREEN, outline="")
                chart.create_text(34 + length + 8, y, anchor="w",
                                  text=_fmt_ms(case_result.runtime_ms),
                                  fill=MUTED, font=self.mono_small)

        chart.bind("<Configure>", draw)

    def _scaling_block(self, parent, sub: Submission) -> None:
        scaling = sub.scaling
        if not scaling:
            self._label(
                parent,
                "Add scaling_input(n) to tests.py to measure how this scales.",
                font=self.small, fg=MUTED,
            ).pack(anchor="w", padx=14, pady=(8, 0))
            return
        if scaling.get("error"):
            self._label(parent, f"Complexity: {scaling['error']}",
                        font=self.small, fg=YELLOW,
                        wraplength=getattr(self, "_wrap", 900)).pack(
                anchor="w", padx=14, pady=(8, 0))
            return

        rows: List[Dict[str, Any]] = scaling.get("rows") or []
        if not rows:
            return

        self._label(parent, "Measured complexity", font=self.small,
                    fg=MUTED).pack(anchor="w", padx=14, pady=(12, 4))

        summary = tk.Frame(parent, bg=PANEL)
        summary.pack(fill="x", padx=8)
        for key, title in (("time", "Time"), ("space", "Space")):
            block = scaling.get(key) or {}
            tile = tk.Frame(summary, bg=INSET)
            tile.pack(side="left", fill="both", expand=True, padx=6, pady=4)
            self._label(tile, title, font=self.small, fg=MUTED, bg=INSET).pack(
                anchor="w", padx=14, pady=(10, 0))
            self._label(tile, block.get("label", "?"), font=self.h2,
                        fg=GREEN, bg=INSET).pack(anchor="w", padx=14)
            detail = f"fit {block.get('fit', 0):.3f}"
            if block.get("exponent") is not None:
                detail += f"   log-log slope {block['exponent']:.2f}"
            self._label(tile, detail, font=self.small, fg=MUTED, bg=INSET).pack(
                anchor="w", padx=14, pady=(0, 10))

        table = tk.Frame(parent, bg=INSET)
        table.pack(fill="x", padx=14, pady=(8, 0))
        header = f"{'n':>8}   {'time':>12}   {'space':>12}"
        self._label(table, header, font=self.mono_small, fg=MUTED,
                    bg=INSET).pack(anchor="w", padx=12, pady=(8, 2))
        for row in rows:
            line = (f"{row['n']:>8}   {_fmt_ms(row['ms']):>12}   "
                    f"{_fmt_kb(row['kb']):>12}")
            self._label(table, line, font=self.mono_small, fg=FG,
                        bg=INSET).pack(anchor="w", padx=12)
        tk.Frame(table, bg=INSET, height=8).pack()

        self._label(
            parent,
            "Measured on this machine, from your own runs - not a comparison "
            "against other people's submissions.",
            font=self.small, fg=MUTED, wraplength=getattr(self, "_wrap", 900),
        ).pack(anchor="w", padx=14, pady=(8, 0))

    def _section_case_list(self, sub: Submission) -> None:
        card = self._card()
        title = "Testcases" if sub.accepted else f"Testcases  -  {len(sub.failures)} failing"
        self._label(card, title, font=self.h2).pack(anchor="w", padx=14,
                                                    pady=(12, 6))
        listing = tk.Frame(card, bg=PANEL)
        listing.pack(fill="x", padx=8, pady=(0, 10))
        for case_result in sub.cases:
            self._case_row(listing, case_result)

    def _case_row(self, parent, case_result: CaseResult) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=6, pady=1)
        if case_result.ok:
            glyph, color, note = "✓", GREEN, _fmt_ms(case_result.runtime_ms)
            note_color = MUTED
        elif case_result.status == "error":
            glyph, color = "✗", RED
            note = (case_result.error or {}).get("type", "Error")
            note_color = RED
        else:
            glyph, color, note, note_color = "✗", RED, "Wrong Answer", RED

        tk.Label(row, text=glyph, font=self.ui_bold, bg=PANEL, fg=color,
                 width=2).pack(side="left")
        tk.Label(row, text=f"Case {case_result.number}", font=self.mono_small,
                 bg=PANEL, fg=MUTED, width=9, anchor="w").pack(side="left")
        tk.Label(row, text=note, font=self.small, bg=PANEL, fg=note_color,
                 width=18, anchor="e").pack(side="right")
        tk.Label(row, text=case_result.name, font=self.ui, bg=PANEL,
                 fg=FG if not case_result.ok else MUTED,
                 anchor="w").pack(side="left", fill="x", expand=True)

    def _section_failures(self, sub: Submission) -> None:
        for case_result in sub.failures:
            card = self._card()
            head = tk.Frame(card, bg=PANEL)
            head.pack(fill="x", padx=14, pady=(12, 0))
            tk.Label(head, text=f"Case {case_result.number}", font=self.h2,
                     bg=PANEL, fg=FG).pack(side="left")
            tk.Label(head, text=f"   {case_result.name}", font=self.ui,
                     bg=PANEL, fg=MUTED).pack(side="left")

            if case_result.args_repr:
                for key, value in case_result.args_repr.items():
                    self._field(card, "Input" if key == list(
                        case_result.args_repr)[0] else "", f"{key} = {value}")
            else:
                self._field(card, "Input", "(no arguments)")

            if case_result.stdout.strip():
                self._field(card, "Stdout", case_result.stdout.rstrip(), MUTED)

            if case_result.status == "error":
                error = case_result.error or {}
                self._field(card, "Output",
                            f"{error.get('type')}: {error.get('message')}", RED)
                if error.get("line"):
                    where = (f"Line {error['line']} in "
                             f"{error.get('func') or '<module>'} "
                             f"({error.get('file')})")
                    self._label(card, where, font=self.small, fg=MUTED).pack(
                        anchor="w", padx=14)
                    if error.get("code"):
                        self._label(card, error["code"], font=self.mono_small,
                                    fg=MUTED).pack(anchor="w", padx=28,
                                                   pady=(2, 0))
            else:
                self._field(card, "Output", case_result.output_repr or "None", RED)

            self._field(card, "Expected", case_result.expected_repr, GREEN)
            tk.Frame(card, bg=PANEL, height=10).pack()

    # ---------------------------------------------------------------- extras

    def copy_report(self) -> None:
        sub = self.submission
        if sub is None:
            return
        lines = [f"{sub.verdict}  -  {self.problem.slug}"]
        if sub.total:
            lines.append(f"{sub.passed} / {sub.total} testcases passed")
        lines.append("")
        for case_result in sub.cases:
            mark = "PASS" if case_result.ok else "FAIL"
            lines.append(f"[{mark}] Case {case_result.number}  {case_result.name}")
        for case_result in sub.failures:
            lines.append("")
            lines.append(f"Case {case_result.number}  {case_result.name}")
            for key, value in case_result.args_repr.items():
                lines.append(f"  Input     {key} = {value}")
            if case_result.status == "error":
                error = case_result.error or {}
                lines.append(f"  Output    {error.get('type')}: {error.get('message')}")
            else:
                lines.append(f"  Output    {case_result.output_repr}")
            lines.append(f"  Expected  {case_result.expected_repr}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))

    def run(self) -> int:
        self.root.after(60, self.rerun)
        self.root.mainloop()
        sub = self.submission
        return 0 if (sub is not None and sub.accepted) else 1


def launch(problem: Problem, timeout: float = 10.0,
           with_scaling: bool = True) -> int:
    return ResultsWindow(problem, timeout=timeout,
                         with_scaling=with_scaling).run()
