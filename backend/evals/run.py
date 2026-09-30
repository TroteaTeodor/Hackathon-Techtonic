"""A/B evaluation of life-moment detection variants, plus guardrail checks on the resulting interventions.

    docker compose exec backend python -m evals.run                      # all variants
    docker compose exec backend python -m evals.run --variants rules,gemini:gemini-3.8-flash:low --limit 40

Variants: "rules", "jev" (OpenRouter Decisions API), or "gemini:<model>[:<thinking level>]".
Add variants to an earlier run with --append evals/results/<file>.json. Writes evals/results/<timestamp>.json and evals/REPORT.md.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import settings
from app.detection import gemini, jev, recent, rules
from app.interventions import plan
from app.twin import build_twin
from evals import metrics
from evals.dataset import build

DEFAULT_VARIANTS = ["rules", "gemini:gemini-3.8-flash", "gemini:gemini-3.8-flash:low", "gemini:gemini-3.5-flash:low"]
EVAL_TIMEOUT_S = 30  # generous, so we measure the model; >10s would fall back to rules in production
TODAY = date.today()
OUT = Path(__file__).parent


def run_case(variant: str, case) -> dict:
    signals = recent(case.signals)
    started = time.perf_counter()
    error = None
    if variant == "rules":
        det = rules.detect(case.customer, signals)
    elif variant == "jev":
        det = None
        for attempt in range(3):
            try:
                det = jev.detect(case.customer, signals, timeout_seconds=EVAL_TIMEOUT_S)
                error = None
                break
            except Exception as err:
                error = type(err).__name__ + ": " + str(err)[:120]
                if "429" not in str(err) and "50" not in str(err):
                    break
                time.sleep(2 * (attempt + 1))
        if det is None:
            det = rules.detect(case.customer, signals)
    else:
        _, model, *rest = variant.split(":")
        thinking = rest[0] if rest else ""
        det = None
        for attempt in range(3):  # retry rate limits / transient 5xx
            try:
                det = gemini.detect(case.customer, signals, model=model, thinking=thinking,
                                    timeout_seconds=EVAL_TIMEOUT_S, raise_errors=True)
                error = None if det else "invalid_response"
                break
            except Exception as err:
                error = type(err).__name__ + ": " + str(err)[:120]
                if "429" not in str(err) and "503" not in str(err) and "500" not in str(err):
                    break
                time.sleep(2 * (attempt + 1))
        if det is None:  # production behaviour: fall back to rules
            det = rules.detect(case.customer, signals)
    elapsed = time.perf_counter() - started

    twin = build_twin(case.customer.balance, case.signals, det.key, det.confidence)
    items = plan(case.customer, det, twin, TODAY)
    return {
        "id": case.id, "group": case.group, "label": case.label, "note": case.note,
        "pred": det.key, "confidence": det.confidence, "stress": det.stress, "source": det.source,
        "correct": det.key == case.label, "error": error,
        "latency_s": elapsed if variant != "rules" else None,
        "input_tokens": det.input_tokens, "output_tokens": det.output_tokens, "cost_usd": det.cost_usd,
        "consent": case.customer.marketing_consent,
        "interventions": [{"key": i["key"], "line": i["line"], "status": i["status"], "reasons": len(i["reasons"])} for i in items],
    }


SALES_LINES = {"banking", "insurance", "investing"}


def guardrails(rows) -> dict:
    """Invariants that must hold for every customer, whatever the detector says."""
    violations = {"stressed_got_sales": 0, "no_consent_got_sales": 0, "missing_reasons": 0}
    true_stress_sold = 0
    for r in rows:
        delivered_sales = [i for i in r["interventions"] if i["status"] == "delivered" and i["line"] in SALES_LINES
                           and not i["key"].startswith("pinch")]
        if r["stress"] >= 0.6 and delivered_sales:
            violations["stressed_got_sales"] += 1
        if not r["consent"] and delivered_sales:
            violations["no_consent_got_sales"] += 1
        if any(i["reasons"] == 0 for i in r["interventions"]):
            violations["missing_reasons"] += 1
        if r["label"] == "financial_stress" and delivered_sales:
            true_stress_sold += 1
    stressed = [r for r in rows if r["label"] == "financial_stress"]
    moments = [r for r in rows if r["label"] not in ("no_clear_moment", "financial_stress")]
    reached = sum(1 for r in moments if r["pred"] == r["label"]
                  and any(i["status"] in ("delivered", "review") and not i["key"].startswith(("pinch", "surplus")) for i in r["interventions"]))
    wrong_delivered = sum(1 for r in rows if r["pred"] != r["label"] and r["pred"] not in ("no_clear_moment", "financial_stress")
                          and any(i["status"] == "delivered" and not i["key"].startswith(("pinch", "surplus")) for i in r["interventions"]))
    return {
        **violations,
        "harmful_sales_rate": true_stress_sold / len(stressed) if stressed else 0.0,
        "right_moment_reached_rate": reached / len(moments) if moments else 0.0,
        "wrong_moment_delivered_rate": wrong_delivered / len(rows) if rows else 0.0,
    }


def summarize(variant, rows) -> dict:
    by_group = {g: metrics.accuracy([r for r in rows if r["group"] == g]) for g in ("story", "population", "hard")}
    ai = [r for r in rows if r["source"] in ("gemini", "jev")]
    tin = sum(r["input_tokens"] for r in ai) / len(ai) if ai else 0
    tout = sum(r["output_tokens"] for r in ai) / len(ai) if ai else 0
    reported = [r["cost_usd"] for r in ai if r.get("cost_usd") is not None]
    if reported:  # Jev reports its real cost (USD); treated as EUR at ~parity for the projection
        cost = sum(reported) / len(reported)
    else:
        cost = (tin * settings.price_per_million_input_tokens_eur + tout * settings.price_per_million_output_tokens_eur) / 1e6
    return {
        "variant": variant, "n": len(rows),
        "accuracy": metrics.accuracy(rows), "accuracy_by_group": by_group, "macro_f1": metrics.macro_f1(rows),
        "recall_per_class": metrics.recall_per_class(rows), "stress": metrics.stress_detection(rows),
        "calibration": metrics.calibration(rows), "latency": metrics.latency(rows),
        "fallback_rate": sum(1 for r in rows if r["error"]) / len(rows) if variant != "rules" else 0.0,
        "avg_input_tokens": tin, "avg_output_tokens": tout, "cost_per_analysis_eur": cost,
        "projected_daily_cost_eur": cost * settings.projection_customers * settings.daily_reevaluation_rate,
        "top_confusions": metrics.confusion(rows), "guardrails": guardrails(rows),
    }


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}%"


def report(summaries, pairs, cases_n, rows_by_variant) -> str:
    first = rows_by_variant[summaries[0]["variant"]]
    counts = {g: sum(1 for r in first if r["group"] == g) for g in ("story", "population", "hard")}
    lines = [
        "# Moment-detection evals (A/B)", "",
        f"Run {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} on {cases_n} labelled cases "
        f"({counts.get('story', 0)} story, {counts.get('population', 0)} generated population, {counts.get('hard', 0)} hard cases).",
        f"Costs use the configured price assumptions (€{settings.price_per_million_input_tokens_eur}/M input, "
        f"€{settings.price_per_million_output_tokens_eur}/M output tokens) — verify against the Google Cloud price list.", "",
        "## Headline", "",
        "| Variant | Accuracy | Macro-F1 | Story | Population | Hard | Stress recall | ECE | p50 / p95 latency | >10s | Fallbacks | Cost / 1k analyses | Daily @2.3M×5% |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lat = s["latency"]
        lat_txt = "—" if lat["p50"] is None else f"{lat['p50']:.1f}s / {lat['p95']:.1f}s"
        g = s["accuracy_by_group"]
        lines.append(
            f"| `{s['variant']}` | {pct(s['accuracy'])} | {s['macro_f1']:.3f} | {pct(g['story'])} | {pct(g['population'])} | "
            f"{pct(g['hard'])} | {pct(s['stress']['recall'])} | {s['calibration']['ece']:.3f} | {lat_txt} | {lat['over_10s']} | "
            f"{pct(s['fallback_rate'])} | €{s['cost_per_analysis_eur'] * 1000:.2f} | €{s['projected_daily_cost_eur']:.0f} |")
    lines += ["", "## Paired significance vs rules (exact McNemar)", "",
              "| Variant | Only this variant correct | Only rules correct | p-value |", "|---|---|---|---|"]
    for variant, p in pairs.items():
        lines.append(f"| `{variant}` | {p['b_only_correct']} | {p['a_only_correct']} | {p['p_value']:.2g} |")
    lines += ["", "## Guardrails (must be 0)", "",
              "| Variant | Stressed got sales | No consent got sales | Missing reasons | Harmful sales rate | Right moment reached | Wrong moment delivered |",
              "|---|---|---|---|---|---|---|"]
    for s in summaries:
        gr = s["guardrails"]
        lines.append(f"| `{s['variant']}` | {gr['stressed_got_sales']} | {gr['no_consent_got_sales']} | {gr['missing_reasons']} | "
                     f"{pct(gr['harmful_sales_rate'])} | {pct(gr['right_moment_reached_rate'])} | {pct(gr['wrong_moment_delivered_rate'])} |")
    lines += ["", "## Calibration (accuracy by confidence band)", ""]
    for s in summaries:
        bands = ", ".join(f"{b['band']}: {pct(b['accuracy'])} (n={b['n']})" for b in s["calibration"]["bands"])
        lines.append(f"- `{s['variant']}`: {bands}")
    lines += ["", "## Hard cases", "", "| Case | Label | " + " | ".join(f"`{s['variant']}`" for s in summaries) + " |",
              "|---|---|" + "---|" * len(summaries)]
    hard_ids = [r["id"] for r in rows_by_variant[summaries[0]["variant"]] if r["group"] == "hard"]
    for cid in hard_ids:
        row = next(r for r in rows_by_variant[summaries[0]["variant"]] if r["id"] == cid)
        cells = []
        for s in summaries:
            r = next(x for x in rows_by_variant[s["variant"]] if x["id"] == cid)
            cells.append(("✅ " if r["correct"] else "❌ ") + r["pred"])
        lines.append(f"| {row['note']} | {row['label']} | " + " | ".join(cells) + " |")
    lines += ["", "## Most common confusions (label → predicted)", ""]
    for s in summaries:
        conf = ", ".join(f"{a}→{b} ×{n}" for (a, b), n in s["top_confusions"]) or "none"
        lines.append(f"- `{s['variant']}`: {conf}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    parser.add_argument("--limit", type=int, default=0, help="population cases to include (0 = all)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--append", help="results JSON from an earlier run: keep its variants and add these")
    args = parser.parse_args()

    cases = build(TODAY)
    if args.limit:
        pop = [c for c in cases if c.group == "population"][: args.limit]
        cases = [c for c in cases if c.group != "population"] + pop
    variants = args.variants.split(",")
    if any(v.startswith("gemini") for v in variants) and not gemini.is_configured():
        raise SystemExit("Gemini is not configured")
    if "jev" in variants and not jev.is_configured():
        raise SystemExit("OPENROUTER_API_KEY is not set")

    rows_by_variant, summaries = {}, []
    if args.append:
        previous = json.loads(Path(args.append).read_text())
        rows_by_variant = previous["rows"]
        summaries = [s for s in previous["summaries"] if s["variant"] not in variants]
    for variant in variants:
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=1 if variant == "rules" else args.workers) as pool:
            rows = list(pool.map(lambda c: run_case(variant, c), cases))
        rows_by_variant[variant] = rows
        summaries.append(summarize(variant, rows))
        print(f"{variant}: accuracy {pct(summaries[-1]['accuracy'])} in {time.perf_counter() - started:.0f}s", flush=True)

    all_variants = [s["variant"] for s in summaries]
    pairs = {v: metrics.mcnemar(rows_by_variant["rules"], rows_by_variant[v]) for v in all_variants if v != "rules"} if "rules" in rows_by_variant else {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (OUT / "results").mkdir(exist_ok=True)
    (OUT / "results" / f"{stamp}.json").write_text(json.dumps(
        {"summaries": summaries, "pairs": pairs, "rows": rows_by_variant}, indent=1, default=str))
    (OUT / "REPORT.md").write_text(report(summaries, pairs, len(cases), rows_by_variant))
    print(f"wrote evals/REPORT.md and evals/results/{stamp}.json")


if __name__ == "__main__":
    main()
