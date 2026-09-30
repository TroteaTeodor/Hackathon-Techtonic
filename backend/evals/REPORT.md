# Moment-detection evals (A/B)

Run 2026-09-30 17:24 UTC on 220 labelled cases (7 story, 200 generated population, 13 hard cases).
Costs use the configured price assumptions (€0.3/M input, €2.5/M output tokens) — verify against the Google Cloud price list.

## Headline

| Variant | Accuracy | Macro-F1 | Story | Population | Hard | Stress recall | ECE | p50 / p95 latency | >10s | Fallbacks | Cost / 1k analyses | Daily @2.3M×5% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `rules` | 94.5% | 0.953 | 100.0% | 100.0% | 7.7% | 80.0% | 0.217 | — | 0 | 0.0% | €0.00 | €0 |

## Paired significance vs rules (exact McNemar)

| Variant | Only this variant correct | Only rules correct | p-value |
|---|---|---|---|

## Guardrails (must be 0)

| Variant | Stressed got sales | No consent got sales | Missing reasons | Harmful sales rate | Right moment reached | Wrong moment delivered |
|---|---|---|---|---|---|---|
| `rules` | 0 | 0 | 0 | 0.0% | 37.9% | 0.5% |

## Calibration (accuracy by confidence band)

- `rules`: 0.00-0.50: 100.0% (n=5), 0.50-0.75: 91.9% (n=135), 0.75-1.00: 98.8% (n=80)

## Hard cases

| Case | Label | `rules` |
|---|---|---|
| notary for an inheritance, not a home purchase | no_clear_moment | ❌ moving_home |
| yearly pension savings at 30 is routine, not retirement | no_clear_moment | ❌ approaching_retirement |
| gift for someone else's baby | no_clear_moment | ❌ growing_family |
| car dealer for maintenance, not a purchase | no_clear_moment | ❌ buying_car |
| airline refund for a cancelled trip | no_clear_moment | ❌ travel_abroad |
| moving described through movers, rental guarantee and new utilities | moving_home | ❌ no_clear_moment |
| newborn described through diapers and child allowance | growing_family | ❌ no_clear_moment |
| salary from a new employer, no job keywords | new_job | ❌ no_clear_moment |
| stress through buy-now-pay-later, mini loans and declined cards | financial_stress | ❌ no_clear_moment |
| end of career through a group-insurance payout | approaching_retirement | ❌ no_clear_moment |
| trip described through foreign card payments | travel_abroad | ❌ no_clear_moment |
| car purchase through second-hand listing and registration | buying_car | ❌ no_clear_moment |
| control: routine month with a big grocery run | no_clear_moment | ✅ no_clear_moment |

## Most common confusions (label → predicted)

- `rules`: no_clear_moment→moving_home ×1, no_clear_moment→approaching_retirement ×1, no_clear_moment→growing_family ×1, no_clear_moment→buying_car ×1, no_clear_moment→travel_abroad ×1, moving_home→no_clear_moment ×1, growing_family→no_clear_moment ×1, new_job→no_clear_moment ×1
