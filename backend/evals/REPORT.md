# Moment-detection evals (A/B)

Run 2026-09-30 18:40 UTC on 340 labelled cases (7 story, 200 generated population, 133 hard cases).
Costs use the configured price assumptions (€0.3/M input, €2.5/M output tokens) — verify against the Google Cloud price list.

## Headline

| Variant | Accuracy | Macro-F1 | Story | Population | Hard | Stress recall | ECE | p50 / p95 latency | >10s | Fallbacks | Cost / 1k analyses | Daily @2.3M×5% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `rules` | 61.8% | 0.645 | 100.0% | 100.0% | 2.3% | 39.4% | 0.172 | — | 0 | 0.0% | €0.00 | €0 |
| `jev` | 94.1% | 0.953 | 100.0% | 92.5% | 96.2% | 100.0% | 0.023 | 0.3s / 0.5s | 0 | 0.0% | €0.10 | €11 |
| `gemini:gemini-3.8-flash:low` | 96.5% | 0.971 | 100.0% | 95.0% | 98.5% | 97.0% | 0.060 | 3.1s / 9.9s | 16 | 1.2% | €1.14 | €131 |
| `gemini:gemini-3.8-flash` | 95.9% | 0.965 | 100.0% | 95.5% | 96.2% | 100.0% | 0.073 | 5.8s / 16.5s | 58 | 2.4% | €1.99 | €229 |
| `gemini:gemini-3.5-flash:low` | 95.6% | 0.961 | 100.0% | 96.5% | 94.0% | 97.0% | 0.056 | 2.4s / 27.5s | 40 | 6.2% | €1.30 | €149 |
| `app` | 96.2% | 0.969 | 100.0% | 95.0% | 97.7% | 100.0% | 0.021 | 0.3s / 3.8s | 6 | 0.0% | €0.25 | €28 |

## Paired significance vs rules (exact McNemar)

| Variant | Only this variant correct | Only rules correct | p-value |
|---|---|---|---|
| `jev` | 126 | 16 | 2.2e-22 |
| `gemini:gemini-3.8-flash:low` | 129 | 11 | 1.1e-26 |
| `gemini:gemini-3.8-flash` | 126 | 10 | 1.1e-26 |
| `gemini:gemini-3.5-flash:low` | 123 | 8 | 1.4e-27 |
| `app` | 128 | 11 | 2e-26 |

## Head to head: Gemini variants vs Jev (exact McNemar)

| Variant | Only Gemini correct | Only Jev correct | p-value |
|---|---|---|---|
| `gemini:gemini-3.8-flash:low` | 12 | 4 | 0.077 |
| `gemini:gemini-3.8-flash` | 13 | 7 | 0.26 |
| `gemini:gemini-3.5-flash:low` | 16 | 11 | 0.44 |
| `app` | 10 | 3 | 0.092 |

## Cascade (simulated from the rows above)

Jev answers when its confidence is ≥ 75%; otherwise the case is escalated to `gemini:gemini-3.8-flash:low`. 40 of 340 cases (11.8%) escalated.

| Variant | Accuracy | Macro-F1 | Story | Population | Hard | p50 / p95 latency | Cost / 1k analyses | Daily @2.3M×5% | Stressed got sales |
|---|---|---|---|---|---|---|---|---|---|
| cascade | 96.5% | 0.971 | 100.0% | 95.0% | 98.5% | 0.3s / 4.0s | €0.23 | €27 | 0 |

Cascade vs `gemini:gemini-3.8-flash:low` alone: 1 cases only the cascade gets right, 1 only Gemini gets right (p = 1).

## Guardrails (must be 0)

| Variant | Stressed got sales | No consent got sales | Missing reasons | Harmful sales rate | Right moment reached | Wrong moment delivered |
|---|---|---|---|---|---|---|
| `rules` | 0 | 0 | 0 | 3.0% | 23.5% | 1.8% |
| `jev` | 0 | 0 | 0 | 0.0% | 70.9% | 0.0% |
| `gemini:gemini-3.8-flash:low` | 0 | 0 | 0 | 0.0% | 71.8% | 0.6% |
| `gemini:gemini-3.8-flash` | 0 | 0 | 0 | 0.0% | 71.4% | 0.9% |
| `gemini:gemini-3.5-flash:low` | 0 | 0 | 0 | 0.0% | 70.4% | 0.3% |
| `app` | 0 | 0 | 0 | 0.0% | 73.2% | 0.6% |

## Calibration (accuracy by confidence band)

- `rules`: 0.00-0.50: 62.5% (n=8), 0.50-0.75: 51.0% (n=247), 0.75-1.00: 92.9% (n=85)
- `jev`: 0.00-0.50: 50.0% (n=4), 0.50-0.75: 55.6% (n=36), 0.75-1.00: 99.3% (n=300)
- `gemini:gemini-3.8-flash:low`: 0.00-0.50: 100.0% (n=1), 0.50-0.75: 65.2% (n=23), 0.75-1.00: 98.7% (n=316)
- `gemini:gemini-3.8-flash`: 0.00-0.50: 50.0% (n=2), 0.50-0.75: 70.4% (n=27), 0.75-1.00: 98.4% (n=311)
- `gemini:gemini-3.5-flash:low`: 0.00-0.50: 66.7% (n=3), 0.50-0.75: 64.5% (n=31), 0.75-1.00: 99.0% (n=306)
- `app`: 0.00-0.50: — (n=0), 0.50-0.75: 50.0% (n=14), 0.75-1.00: 98.2% (n=326)

## Hard cases

| Case | Label | `rules` | `jev` | `gemini:gemini-3.8-flash:low` | `gemini:gemini-3.8-flash` | `gemini:gemini-3.5-flash:low` | `app` |
|---|---|---|---|---|---|---|---|
| notary for an inheritance, not a home purchase | no_clear_moment | ❌ moving_home | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| yearly pension savings at 30 is routine, not retirement | no_clear_moment | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| gift for someone else's baby | no_clear_moment | ❌ growing_family | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| car dealer for maintenance, not a purchase | no_clear_moment | ❌ buying_car | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| airline refund for a cancelled trip | no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| moving described through movers, rental guarantee and new utilities | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| newborn described through diapers and child allowance | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| salary from a new employer, no job keywords | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| stress through buy-now-pay-later, mini loans and declined cards | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| end of career through a group-insurance payout | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| trip described through foreign card payments | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| car purchase through second-hand listing and registration | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| control: routine month with a big grocery run | no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| paraphrase: Van rental, flat-pack furniture to a different address and a new grid connection; no explicit move word | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Blocked rental-guarantee account plus internet installation and commune registration | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Agency commission and lease registration phrased in Dutch vastgoed terms, no English keyword | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: End-of-lease cleaning and key deposit signal leaving the old flat, not a routine clean | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: French-language removal firm and furniture lift; 'déménagement' is not a rule keyword | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: House purchase shown only via registration duties and deed costs, avoiding the obvious keyword | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Mail forwarding and water meter closing/opening; mundane admin that implies a relocation | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Young adult leaving parents: first rent, deposit and appliances, only everyday merchant names | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Elderly customer downsizing to a service flat; age might mislead a model toward retirement | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Brussels utilities and commune fee in French; needs local knowledge of Sibelga/Vivaqua | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Proceeds from selling a house arriving plus paint and curtains for a new place | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Partners moving in together: one lease ends, shared account opened, second person's registration | moving_home | ❌ no_clear_moment | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| paraphrase: Diapers, infant formula and a Kind en Gezin consultation; no English family keyword | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family |
| paraphrase: Groeipakket start amount plus adding a newborn to the health fund; Flemish admin only | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Pediatrician and infant vaccine payments; must infer a new infant from medical context | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Expecting: ultrasound, NIPT and daycare waitlist, all in Dutch without 'pregnant' | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Postnatal home care and incoming gifts from a geboortelijst; Dutch 'geboorte' avoids the keyword | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Walloon system in French: ONE, Famiwal, mutuelle; 'naissance' is not a rule keyword | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Nursery furniture and an infant car seat purchase with no explicit arrival signal | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Growth via adoption: agency fees and preparation course, no pregnancy or medical signals | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Fertility clinic payments followed by first-trimester follow-up; clinical wording only | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Father's perspective: leave request and hospital stay payment; no mother-side signals | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Twins: double pram and doubled supplies; Dutch 'kinderwagen' instead of the English keyword | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| paraphrase: Second child: toddler moves to a bigger seat, new infant seat bought; ignoring car-purchase angle | growing_family | ❌ no_clear_moment | ✅ growing_family | ✅ growing_family | ✅ growing_family | ❌ no_clear_moment | ✅ growing_family |
| trap: Notary is for settling a late parent's estate, not a property purchase; no move follows | no_clear_moment | ❌ moving_home | ✅ no_clear_moment | ✅ no_clear_moment | ❌ moving_home | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Baby items are gifts for a friend's newborn; customer is single, no other family signals | no_clear_moment | ❌ growing_family | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Mortgage and home insurance are routine for a 14-year-old loan; nothing new is happening | no_clear_moment | ❌ moving_home | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Retired grandmother paying a babysitter and buying a travel cot for grandchildren's visits | no_clear_moment | ✅ no_clear_moment | ❌ approaching_retirement | ❌ approaching_retirement | ❌ approaching_retirement | ❌ approaching_retirement | ❌ approaching_retirement |
| trap: 'Real estate' agency only rents a holiday villa in Spain; the trip is the moment, not a move | travel_abroad | ❌ moving_home | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| trap: Mortgage keyword appears, but a bounced instalment and short-term loans show stress, not a move | financial_stress | ❌ moving_home | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Old firm pays final settlement, a different company pays the wage; no job words used | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Sign-on bonus plus home-office setup; must infer a hire without contract words | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Only the commute changes: old bus pass stopped, new train route, pro-rata pay from another firm | new_job | ❌ no_clear_moment | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Company car + fuel card look like a car purchase, but the payroll source changed | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Dimona registration letter is a hire signal only a domain-aware reader recognises | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ❌ no_clear_moment | ✅ new_job |
| paraphrase: Only perks change: meal-voucher card from a new issuer and a pro-rata wage | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Recent graduate: first real wage, suit purchase, student account converted | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Self-employed stops activity (social fund refund) and starts receiving payroll | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Unemployment allowance replaced by a wage from a metal firm, plus safety shoes | new_job | ❌ no_clear_moment | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Same profession, different hospital pays; parking and uniform hint at a start | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Continuation offer for old employer's health cover and wage from another company | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Laptop bought and refunded by a company, job-hunting subscription ends | new_job | ❌ no_clear_moment | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| paraphrase: Group-insurance capital paid out at 65 and a question about spreading it | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Last wage with end-of-career bonus and a farewell reception, never naming it | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: SWT bridging scheme: RVA allowance plus company supplement at 60 | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Federal service letter on statutory old-age benefit start date, described indirectly | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Annual train pass refunded and a farewell gift from colleagues arrives at 64 | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Advisor contact about annuity vs funds; stops working end of November | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Landingsbaan (4/5 career-end time credit) allowance at 60; wage drops | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Senior association membership and golf club after last payslip; no age words | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement |
| paraphrase: 8% anticipatory levy on long-term savings at 60 plus career-length questions | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Civil servant's last pay, then questions about keeping health cover after work | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Self-employed baker sells shop at 64 and asks how to invest proceeds safely | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| paraphrase: Work phone number taken over privately, final wage with gratification, 60+ hobby course | approaching_retirement | ❌ no_clear_moment | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| trap: Routine tax-deductible pension saving at 30 — not approaching the end of career | no_clear_moment | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Customer chips in for a colleague's retirement gift; the customer is 41 | no_clear_moment | ❌ approaching_retirement | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ❌ approaching_retirement |
| trap: Salary account switching asked by someone only changing banks, same job for 9 years | no_clear_moment | ❌ new_job | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: 85-year-old receiving the usual monthly pension for decades — routine, no moment | no_clear_moment | ❌ approaching_retirement | ✅ no_clear_moment | ❌ approaching_retirement | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Employment contract only requested by a landlord; the real moment is renting a flat | moving_home | ❌ new_job | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| trap: 'Pension' is an Austrian guesthouse: this is a trip, not the end of career | travel_abroad | ❌ approaching_retirement | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Used car bought from a private seller: 2dehands searches, cash deposit and DIV plate fee, no car vocabulary | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: New EV order implied only by garage down payment, home wallbox and a Type 2 charging cable | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Technical inspection 'for sale' of the old car plus Gocar browsing signals replacing it | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Old vehicle struck off insurance with premium refund while plate moves to a newly paid Yaris | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Car imported from Germany: Autohaus payment, transport company and conformity check | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Only a bank contact about financing a specific second-hand model plus Car-Pass check | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Young driver passes exam, pays a deposit for a used Polo and a starter insurance premium | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Dutch 'proefrit' and 'autolening' instead of the English rule phrases | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Trade-in valuation, signed order form and registration tax; no rule wording | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: French-language used-car purchase: acompte, immatriculation and assurance auto devis | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Brand-only payment for a new EV plus scrapping the old diesel at a recycler | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Seven-seater bought via a used-car platform; kids context could distract toward family | buying_car | ❌ no_clear_moment | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| paraphrase: Customer is currently in Portugal: only local card payments and an ATM withdrawal | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Long-haul trip evidenced by KLM ticket, Kenyan eTA fee and tropical-medicine vaccine visit | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ❌ no_clear_moment | ✅ travel_abroad |
| paraphrase: Package holiday deposit, suitcase purchase and destination search; no rule keywords | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Eurostar tickets, a UK hotel charged in GBP and a plug adapter | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: US visa waiver (ESTA) fee and transatlantic flight with a non-keyword carrier | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: International driving permit at city hall plus a prepaid rental car in Reykjavik | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: eSIM for Japan, JR rail pass and a yen cash order at the branch | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Transavia flight and a riad deposit charged in dirham | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Bank contact about card use in Thailand plus flight and vaccines; region never named generically | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Interrail pass followed by card payments in Czech koruna and forint | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Road trip visible only via French motorway tolls, fuel and a hotel in Provence | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| paraphrase: Norwegian coastal cruise balance, SAS flight to Bergen and a krone top-up | travel_abroad | ❌ no_clear_moment | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |
| trap: 'dealer' appears, but it is a routine annual service of the car already owned | no_clear_moment | ❌ buying_car | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Airline keyword, but it is an incoming refund for a cancelled flight and no rebooking | no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment | ✅ no_clear_moment | ❌ travel_abroad | ❌ travel_abroad | ❌ travel_abroad |
| trap: Passport renewal only because the old one expired and the bank asked for a KYC ID update | no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment |
| trap: Car insurance quote searches are price-shopping at renewal for a 2019 car already owned | no_clear_moment | ❌ buying_car | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Airbnb credits are recurring host payouts for renting out a room, routine income | no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: 'car loan' is an existing loan going unpaid: failed instalment and a deferral request | financial_stress | ❌ buying_car | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Several buy-now-pay-later instalments at once, near-zero balance; no rule keyword present | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Two consumer mini-loan payouts in a week look like income but signal borrowing to cover costs | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Card refused for lack of funds at a supermarket, split basket retry; no stress keyword used | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Bailiff (gerechtsdeurwaarder) fee payment; enforcement stage of debt, no English keyword | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Incoming social-welfare aid from the CPAS looks like ordinary income | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Cash from pawning jewellery at the Berg van Barmhartigheid, immediately spent on bills | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Salary roughly halved and replaced partly by temporary-unemployment benefit; account now negative | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Repeated betting deposits while the balance is negative; gambling spend, not entertainment | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Only signal is a request to postpone a loan instalment; must not be read as loan interest | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Energy supplier arrears leading to a prepaid budget meter; Belgian-specific stress signal | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Customer seeks debt counselling at CAW; searches and appointment, no transactions | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Rent standing order not executed for lack of funds plus selling belongings online | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Credit card maxed out and repeated small transfers from a parent to bridge until payday | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| paraphrase: Tax bill the customer cannot pay, asks the tax office for spread payments in Dutch wording | financial_stress | ❌ no_clear_moment | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| trap: Overdraft facility auto-renewed but never used; healthy balance means no stress | no_clear_moment | ❌ financial_stress | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: 'Missed' appears in a one-off parking fine already paid; otherwise routine | no_clear_moment | ❌ financial_stress | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Gift to a friend's birth list at 61; the baby is not the customer's | no_clear_moment | ❌ growing_family | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: 'Payment plan' is just a gym membership billing scheme, not debt | no_clear_moment | ❌ financial_stress | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Dealer invoice is seasonal tyre maintenance on an existing car, not a purchase | no_clear_moment | ❌ buying_car | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Tax-driven pension savings deposit at 29 is routine, not approaching retirement | no_clear_moment | ❌ approaching_retirement | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Annual home insurance renewal at the same address for years; not moving | no_clear_moment | ❌ moving_home | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment |
| trap: Booking.com hotel in Antwerp for work, reimbursed by employer; not travel abroad | no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment | ✅ no_clear_moment | ✅ no_clear_moment | ❌ travel_abroad | ✅ no_clear_moment |
| trap: Travel insurance and one-way flight hide that a salary from a new German employer has started | new_job | ❌ travel_abroad | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job | ✅ new_job |
| trap: Notary fee is for a parent's estate; collection letters and negative balance show stress | financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| trap: Car-loan simulator search, but salary stopped and card declined; must not push a car loan | financial_stress | ❌ buying_car | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress | ✅ financial_stress |
| trap: Passport fee for a newborn looks like travel; birth allowance and maternity care make it family | growing_family | ❌ travel_abroad | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family | ✅ growing_family |
| trap: Overdraft keyword but healthy savings; 64-year-old planning the end of his working life | approaching_retirement | ❌ financial_stress | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement | ✅ approaching_retirement |
| trap: 'Cash advance' is an employer relocation advance; rental deposit and movers show a move | moving_home | ❌ financial_stress | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home | ✅ moving_home |
| trap: 'Payment plan' is for financing a used car purchase with a large healthy balance | buying_car | ❌ financial_stress | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car | ✅ buying_car |
| trap: 'Missed' refers to a flight connection; foreign card spend shows a trip abroad, not stress | travel_abroad | ❌ financial_stress | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad | ✅ travel_abroad |

## Most common confusions (label → predicted)

- `rules`: financial_stress→no_clear_moment ×15, moving_home→no_clear_moment ×13, growing_family→no_clear_moment ×13, new_job→no_clear_moment ×13, approaching_retirement→no_clear_moment ×13, travel_abroad→no_clear_moment ×13, buying_car→no_clear_moment ×13, no_clear_moment→approaching_retirement ×5
- `jev`: no_clear_moment→approaching_retirement ×10, new_job→no_clear_moment ×4, travel_abroad→no_clear_moment ×3, moving_home→no_clear_moment ×2, moving_home→approaching_retirement ×1
- `gemini:gemini-3.8-flash:low`: moving_home→no_clear_moment ×4, no_clear_moment→approaching_retirement ×3, travel_abroad→no_clear_moment ×2, new_job→no_clear_moment ×2, growing_family→no_clear_moment ×1
- `gemini:gemini-3.8-flash`: moving_home→no_clear_moment ×4, travel_abroad→no_clear_moment ×2, new_job→no_clear_moment ×2, no_clear_moment→approaching_retirement ×2, new_job→moving_home ×1, growing_family→no_clear_moment ×1, no_clear_moment→moving_home ×1, no_clear_moment→travel_abroad ×1
- `gemini:gemini-3.5-flash:low`: new_job→no_clear_moment ×3, no_clear_moment→travel_abroad ×3, travel_abroad→no_clear_moment ×2, new_job→moving_home ×2, growing_family→no_clear_moment ×2, growing_family→approaching_retirement ×1, no_clear_moment→approaching_retirement ×1, approaching_retirement→no_clear_moment ×1
- `app`: moving_home→no_clear_moment ×4, no_clear_moment→approaching_retirement ×3, new_job→no_clear_moment ×3, travel_abroad→no_clear_moment ×2, no_clear_moment→travel_abroad ×1
