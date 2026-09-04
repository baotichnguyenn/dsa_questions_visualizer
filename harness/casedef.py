"""Test-case definition shared by the runner and by pytest."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

RESERVED = ("name", "expected", "checker")


@dataclass
class Case:
    """One testcase: named arguments in, one expected value out."""

    name: str
    args: Dict[str, Any]
    expected: Any
    checker: Optional[Callable[[Any, Any], bool]] = None

    def matches(self, actual: Any) -> bool:
        if self.checker is not None:
            return bool(self.checker(actual, self.expected))
        return actual == self.expected

    @property
    def positional(self) -> List[Any]:
        return list(self.args.values())


def case(name: str, *, expected: Any, checker=None, **args: Any) -> Case:
    """Build a Case.

    Every keyword other than ``expected``/``checker`` becomes a named argument
    passed to the solution, in the order written:

        case("Example 1", expected=("valid", 2), events=[("open", 7)])
    """
    return Case(name=name, args=dict(args), expected=expected, checker=checker)


def normalise(raw: Any) -> Case:
    """Accept a Case, a plain dict, or a legacy (name, arg, expected) tuple."""
    if isinstance(raw, Case):
        return raw
    if isinstance(raw, dict):
        return Case(
            name=raw["name"],
            args=dict(raw.get("args", {})),
            expected=raw["expected"],
            checker=raw.get("checker"),
        )
    if isinstance(raw, (tuple, list)) and len(raw) == 3:
        name, arg, expected = raw
        return Case(name=name, args={"arg": arg}, expected=expected)
    raise TypeError(f"Cannot interpret testcase: {raw!r}")


def load_cases(module: Any) -> List[Case]:
    raw = getattr(module, "TEST_CASES", None)
    if raw is None:
        raw = getattr(module, "test_cases", None)
    if raw is None:
        raise AttributeError(
            f"{module.__name__} defines neither TEST_CASES nor test_cases"
        )
    return [normalise(item) for item in raw]


def brief(value: Any, max_len: int = 180, max_items: int = 10) -> str:
    """repr() that stays readable for the big stress cases."""
    try:
        text = repr(value)
    except Exception as exc:  # pragma: no cover - defensive
        return f"<unrepresentable {type(value).__name__}: {exc}>"
    if len(text) <= max_len:
        return text
    if isinstance(value, (list, tuple)) and len(value) > max_items:
        head = ", ".join(repr(x) for x in value[:max_items])
        opener, closer = ("[", "]") if isinstance(value, list) else ("(", ")")
        return f"{opener}{head}, ... +{len(value) - max_items} more{closer}"
    return text[:max_len] + f" ... (+{len(text) - max_len} chars)"
