"""ANSI styling tuned to LeetCode's submission palette."""
import os
import shutil
import sys

_ENABLED = None


def _enable_windows_vt() -> bool:
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        return True
    except Exception:
        return False


def colors_enabled() -> bool:
    global _ENABLED
    if _ENABLED is None:
        if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            _ENABLED = False
        else:
            _ENABLED = _enable_windows_vt()
    return _ENABLED


def _can_encode(sample: str) -> bool:
    """Legacy consoles and piped cp1252 streams cannot take box glyphs."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        sample.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


UNICODE_OK = _can_encode("\u2713\u2717\u00b7\u2500\u203a\u2026")

TICK = "\u2713" if UNICODE_OK else "+"
CROSS = "\u2717" if UNICODE_OK else "x"
DOT = "\u00b7" if UNICODE_OK else "-"
ARROW = "\u203a" if UNICODE_OK else ">"
ELLIPSIS = "\u2026" if UNICODE_OK else "..."
RULE_CHAR = "\u2500" if UNICODE_OK else "-"


def _rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

GREEN = _rgb(0, 184, 163)      # LeetCode "Accepted"
RED = _rgb(239, 71, 67)        # LeetCode "Wrong Answer"
YELLOW = _rgb(255, 161, 22)    # LeetCode "Time Limit Exceeded"
BLUE = _rgb(56, 132, 255)
MUTED = _rgb(138, 138, 138)
WHITE = _rgb(230, 230, 230)


def paint(text: str, *styles: str) -> str:
    if not colors_enabled() or not styles:
        return text
    return "".join(styles) + text + RESET


def width(default: int = 80, cap: int = 100) -> int:
    try:
        cols = shutil.get_terminal_size((default, 24)).columns
    except Exception:
        cols = default
    return max(56, min(cols - 2, cap))


def rule(char: str = "", style: str = MUTED) -> str:
    return paint((char or RULE_CHAR) * width(), style)


def clear_screen() -> None:
    if colors_enabled():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        os.system("cls" if os.name == "nt" else "clear")
