from collections import Counter
from math import comb
from statistics import median

from app.schemas import MOMENT_KEYS

BANDS = [(0.0, 0.5), (0.5, 0.75), (0.75, 1.01)]


def accuracy(rows):
    return sum(r["correct"] for r in rows) / len(rows) if rows else 0.0


def macro_f1(rows):
    scores = []
    for k in MOMENT_KEYS:
        tp = sum(1 for r in rows if r["pred"] == k and r["label"] == k)
        fp = sum(1 for r in rows if r["pred"] == k and r["label"] != k)
        fn = sum(1 for r in rows if r["pred"] != k and r["label"] == k)
        if tp + fp + fn == 0:
            continue
        p = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * p * rc / (p + rc) if p + rc else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def recall_per_class(rows):
    out = {}
    for k in MOMENT_KEYS:
        relevant = [r for r in rows if r["label"] == k]
        if relevant:
            out[k] = sum(r["correct"] for r in relevant) / len(relevant)
    return out


def stress_detection(rows, threshold=0.6):
    tp = sum(1 for r in rows if r["stress"] >= threshold and r["label"] == "financial_stress")
    fp = sum(1 for r in rows if r["stress"] >= threshold and r["label"] != "financial_stress")
    fn = sum(1 for r in rows if r["stress"] < threshold and r["label"] == "financial_stress")
    return {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0}


def calibration(rows):
    bands, ece = [], 0.0
    for lo, hi in BANDS:
        inside = [r for r in rows if lo <= r["confidence"] < hi]
        if not inside:
            bands.append({"band": f"{lo:.2f}-{min(hi, 1):.2f}", "n": 0, "accuracy": None, "mean_confidence": None})
            continue
        acc = accuracy(inside)
        conf = sum(r["confidence"] for r in inside) / len(inside)
        ece += len(inside) / len(rows) * abs(acc - conf)
        bands.append({"band": f"{lo:.2f}-{min(hi, 1):.2f}", "n": len(inside), "accuracy": acc, "mean_confidence": conf})
    return {"bands": bands, "ece": ece}


def latency(rows):
    values = sorted(r["latency_s"] for r in rows if r.get("latency_s") is not None)
    if not values:
        return {"p50": None, "p95": None, "over_10s": 0}
    return {"p50": median(values), "p95": values[min(len(values) - 1, int(0.95 * len(values)))],
            "over_10s": sum(1 for v in values if v > 10)}


def confusion(rows):
    return Counter((r["label"], r["pred"]) for r in rows if not r["correct"]).most_common(8)


def mcnemar(a_rows, b_rows):
    """Exact McNemar test on paired predictions (same cases). Returns discordant counts and two-sided p."""
    a = {r["id"]: r["correct"] for r in a_rows}
    b = {r["id"]: r["correct"] for r in b_rows}
    shared = a.keys() & b.keys()
    only_a = sum(1 for i in shared if a[i] and not b[i])
    only_b = sum(1 for i in shared if b[i] and not a[i])
    n = only_a + only_b
    if n == 0:
        return {"a_only_correct": 0, "b_only_correct": 0, "p_value": 1.0}
    k = min(only_a, only_b)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)
    return {"a_only_correct": only_a, "b_only_correct": only_b, "p_value": p}
