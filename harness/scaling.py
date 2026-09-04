"""Empirical complexity measurement.

LeetCode tells you "beats 88% of submissions", which is a number about other
people. There is no submission population here, so inventing one would be a lie.
What we can measure honestly is how your solution actually scales: run it at
several input sizes, then fit the measurements against the usual complexity
classes and report the closest one along with the raw numbers.
"""
from __future__ import annotations

import copy
import gc
import math
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# Candidate growth curves, cheapest first. f(n) is evaluated at each size and
# fitted as  measurement ~= a * f(n) + b. O(1) is not in here: a flat curve
# explains none of the variance, so R^2 can never select it. Constant growth is
# detected up front by how little the measurements move.
MODELS: Sequence[Tuple[str, Callable[[float], float]]] = (
    ("O(log n)", lambda n: math.log2(max(n, 2))),
    ("O(n)", lambda n: n),
    ("O(n log n)", lambda n: n * math.log2(max(n, 2))),
    ("O(n^2)", lambda n: n * n),
    ("O(n^3)", lambda n: n * n * n),
)

REPEATS = 3

# n and n*log n are nearly collinear over the size range we can afford, so a
# better R^2 alone is not evidence. Within this margin, prefer the simpler curve.
OCCAM_MARGIN = 0.01

# Below this, growth is indistinguishable from measurement noise.
MIN_FIT = 0.80

# Ratio between the largest and smallest measurement below which the curve is
# treated as flat.
FLAT_RATIO = 1.35


def _least_squares(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float]:
    """Fit y = a*x + b, returning (a, b)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    a = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return a, mean_y - a * mean_x


def _r_squared(ys: Sequence[float], predicted: Sequence[float]) -> float:
    mean_y = sum(ys) / len(ys)
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - p) ** 2 for y, p in zip(ys, predicted))
    if total == 0:
        return 1.0
    return max(0.0, 1.0 - residual / total)


def classify(sizes: Sequence[int], values: Sequence[float],
             noise_floor: float = 0.0,
             floor_label: str = "too small to measure") -> Dict[str, Any]:
    """Pick the growth curve that best explains `values` over `sizes`."""
    usable = [(n, v) for n, v in zip(sizes, values) if v is not None]
    if len(usable) < 3:
        return {"label": "not enough data", "fit": 0.0, "exponent": None,
                "candidates": []}

    xs = [float(n) for n, _ in usable]
    ys = [float(v) for _, v in usable]

    # Log-log slope, shown alongside the fitted class as a sanity check.
    positive = [(x, y) for x, y in zip(xs, ys) if x > 0 and y > 0]
    exponent = None
    if len(positive) >= 2:
        exponent, _ = _least_squares(
            [math.log(x) for x, _ in positive],
            [math.log(y) for _, y in positive],
        )

    low, high = min(ys), max(ys)

    if high <= noise_floor:
        return {"label": floor_label, "fit": 0.0, "exponent": exponent,
                "candidates": []}

    if low > 0 and high / low < FLAT_RATIO:
        return {"label": "O(1)", "fit": 1.0, "exponent": exponent,
                "candidates": []}

    scored = []
    for label, f in MODELS:
        basis = [f(x) for x in xs]
        a, b = _least_squares(basis, ys)
        if a < 0:
            continue  # a curve that has to shrink to fit is not the shape
        predicted = [a * t + b for t in basis]
        scored.append({"label": label, "fit": _r_squared(ys, predicted)})

    if not scored:
        return {"label": "no clear fit", "fit": 0.0, "exponent": exponent,
                "candidates": []}

    best_fit = max(item["fit"] for item in scored)
    if best_fit < MIN_FIT:
        ranked = sorted(scored, key=lambda item: item["fit"], reverse=True)
        return {"label": "no clear fit", "fit": best_fit, "exponent": exponent,
                "candidates": ranked[:3]}

    # Occam: of the curves that explain the data about equally well, the
    # cheapest one wins. MODELS is already ordered cheapest-first.
    chosen = next(item for item in scored if item["fit"] >= best_fit - OCCAM_MARGIN)
    ranked = sorted(scored, key=lambda item: item["fit"], reverse=True)

    return {
        "label": chosen["label"],
        "fit": chosen["fit"],
        "exponent": exponent,
        "candidates": ranked[:3],
    }


def measure(
    fn: Callable[..., Any],
    build: Callable[[int], Dict[str, Any]],
    sizes: Sequence[int],
) -> Optional[Dict[str, Any]]:
    """Time and measure peak memory for `fn` at each size in `sizes`.

    `build(n)` returns the keyword arguments for one run. Inputs are built and
    copied outside the measured region, so what comes back is the solution's own
    time and auxiliary space, not the cost of constructing its input.
    """
    rows: List[Dict[str, Any]] = []

    for n in sizes:
        try:
            args = list(build(n).values())
        except BaseException as exc:
            return {"error": f"scaling_input({n}) raised {type(exc).__name__}: {exc}"}

        best_ms = None
        for _ in range(REPEATS):
            payload = copy.deepcopy(args)
            gc.collect()
            started = time.perf_counter()
            try:
                fn(*payload)
            except BaseException as exc:
                return {"error": f"solution raised at n={n}: {type(exc).__name__}: {exc}"}
            elapsed = (time.perf_counter() - started) * 1000
            best_ms = elapsed if best_ms is None else min(best_ms, elapsed)

        payload = copy.deepcopy(args)
        gc.collect()
        tracemalloc.start()
        baseline = tracemalloc.get_traced_memory()[0]
        try:
            fn(*payload)
        except BaseException as exc:
            tracemalloc.stop()
            return {"error": f"solution raised at n={n}: {type(exc).__name__}: {exc}"}
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        rows.append({
            "n": n,
            "ms": best_ms,
            "kb": max(0.0, (peak - baseline) / 1024),
        })

    return {
        "rows": rows,
        "time": classify(
            [r["n"] for r in rows], [r["ms"] for r in rows],
            noise_floor=0.05, floor_label="too fast to measure",
        ),
        "space": classify(
            [r["n"] for r in rows], [r["kb"] for r in rows],
            noise_floor=4.0, floor_label="O(1)",
        ),
        "error": None,
    }
