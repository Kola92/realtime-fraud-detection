# Rules, Fraud Scenarios and Evaluation Plan (v1)

Rules and generator scenarios are designed together so the evaluation
tests something real. All thresholds are v1 starting points, tuned on
validation data, never on the test split.

## 1. Rule catalog

Rules are pure functions of the feature vector plus the raw event, so
they are trivially unit-testable. Each hit carries a code, a severity
and a detail string. Only HIGH hits flag an event on their own.

| Code | Severity | Condition |
|---|---|---|
| R001 VELOCITY_BURST | HIGH | count_1h >= 6 |
| R002 IMPOSSIBLE_TRAVEL | HIGH | geo velocity above 900 km/h |
| R003 CARD_TESTING | HIGH | count_1h >= 4 and amount_ngn_minor <= 500000 (NGN 5,000) and channel is card_online |
| R004 TAKEOVER_PATTERN | HIGH | is_new_device and (is_foreign_country or home distance above 300 km) and amount_zscore >= 2.5 |
| R005 ACCOUNT_DRAIN | HIGH | channel is transfer and amount_zscore >= 4 and history_n >= 10 |
| R006 NEW_DEVICE_HIGH_VALUE | MEDIUM | is_new_device and amount_zscore >= 2 |
| R007 MULTI_COUNTRY_24H | MEDIUM | distinct_countries_24h >= 3 |
| R008 ODD_HOUR_FOREIGN | LOW | home-time hour between 01 and 05 and is_foreign_country and channel is card_online |

rules_version is stamped on every scored event.

## 2. Generator scenarios and their legitimate twins

Fraud injected at roughly 1 percent of transactions. Each fraud scenario
has a legitimate twin at a comparable rate, so a detector cannot win by
flagging every unusual transaction.

| Fraud scenario | Pattern | Legitimate twin |
|---|---|---|
| Account takeover | new device, foreign geo, amount 3 to 8 times the account's typical | Legit traveler: foreign geo, known device, normal amounts. New-device upgrade: new device at home location |
| Card testing | 5 to 12 card_online transactions within 10 minutes, NGN 100 to 2,000, mixed merchants | Shopping burst: 3 to 5 normal-amount purchases within an hour |
| Impossible travel | two transactions 20 to 90 minutes apart, cities more than 1,000 km apart | Long-haul travel: same cities with a gap of 6 hours or more |
| Velocity burst | 8 to 15 transactions within 30 minutes at ordinary amounts | Salary day: 4 to 6 bill-payment transfers within an hour |
| Account drain | 1 to 3 transfers at 5 to 15 times typical amount | Rent or fees: one known-payee transfer at 4 to 6 times typical |

Some fraud is deliberately subtle (for example takeover at only 2.5
times typical). Perfect recall on all scenarios means the generator is
too easy.

## 3. Evaluation plan

- Split by time: train on the first part of the simulated period,
  validate on the next, test on the last. Never a random split, because
  per-account state would leak across the boundary.
- The Isolation Forest fits unsupervised on training features. Labels
  are never used in fit.
- The anomaly threshold is chosen on the validation split for a target
  alert rate (starting point: about 1.5 percent), then frozen.
- Report on the test split: precision and recall overall, recall per
  scenario, and PR-AUC.
- Ablation: rules alone, model alone, combined. Per-scenario recall for
  the model alone shows which patterns it misses, which is the most
  honest and most useful table in the write-up.
- All of it is synthetic, so the numbers demonstrate the pipeline, not
  real-world fraud detection performance.
