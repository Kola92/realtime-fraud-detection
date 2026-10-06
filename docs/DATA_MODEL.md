# Data Model and Event Contracts (v1)

Schema first, endpoints later. Everything here is the contract that the
producer, scorer and API share. Money is always integer minor units
(kobo for NGN). Timestamps are UTC ISO 8601 with a trailing Z.

## 1. Redis streams

| Stream | Written by | Read by | Notes |
|---|---|---|---|
| txn.raw | producer | scorer (consumer group `scorers`) | trimmed with MAXLEN |
| txn.scored | scorer | api (plain XREAD, every instance) | trimmed with MAXLEN |
| txn.dead | scorer | operators | invalid or repeatedly failing messages, with reason |

Each stream entry has two fields: `v` (schema version, integer) and
`payload` (one JSON document).

## 2. TransactionEvent (txn.raw, v=1)

| Field | Type | Notes |
|---|---|---|
| txn_id | string (UUID) | idempotency key, derived from the seeded RNG |
| occurred_at | datetime UTC | event time; all windows use this |
| account_id | string | pattern acc_ followed by 6 digits |
| amount_minor | integer | greater than 0, hard upper bound enforced |
| currency | enum | NGN, USD, GBP, EUR |
| merchant_id | string | bounded length |
| merchant_category | string | 4-digit MCC |
| channel | enum | card_present, card_online, transfer, ussd |
| ip | string or null | null for card_present and ussd |
| geo | object | country (ISO 3166 alpha-2), city, lat, lon |
| device_id | string or null | null for card_present and ussd |

Deliberately NOT on the event: account age, home location, any label.

## 3. Account profile (bank-visible fields only)

Stored as a hash at `acct:{id}:profile`: created_at, home_country,
home_city, home_lat, home_lon, home_tz. This is what a bank's CRM or KYC
record would hold. Generator internals (amount distribution, usual
devices, transaction rate) never reach the scorer.

## 4. Redis key layout for feature state

| Key | Type | Content |
|---|---|---|
| acct:{id}:profile | HASH | fields from section 3 |
| acct:{id}:txns | ZSET | score = occurred_at ms, member = txn_id:amount_minor, trimmed to 24h |
| acct:{id}:stats | HASH | n, mean, m2 of ln(amount_minor), Welford running update |
| acct:{id}:devices | ZSET | device_id with last-seen ms, size-capped |
| acct:{id}:merchants | ZSET | merchant_id with last-seen ms, size-capped |
| acct:{id}:countries | ZSET | country with last-seen ms, size-capped |
| acct:{id}:last | HASH | ts, lat, lon of the previous transaction |
| dedupe:{txn_id} | STRING | SET NX with 24h expiry; scorer idempotency |
| truth:{txn_id} | STRING | scenario label, 24h expiry; evaluation only |

## 5. Feature vector v1 (21 columns, fixed order)

| Feature | Definition |
|---|---|
| log_amount | ln(amount_minor) |
| amount_zscore | z-score of log_amount against the account's own history; 0 if history is under 5 |
| history_n | prior transaction count, capped at 50 |
| count_1h, count_24h | prior transactions in the window |
| log_sum_1h | log1p of the summed prior amounts in the last hour |
| log_secs_since_last | log1p of seconds since the previous transaction, capped at 30 days |
| distinct_devices_24h | distinct devices seen in the last 24h, prior state |
| distinct_countries_24h | same, for countries |
| is_new_device, is_new_merchant | 1 if never seen on this account |
| log_geo_velocity_kmh | log1p of implied speed from the previous location; time delta floored at 60s, speed capped at 5000 km/h; 0 with no prior location |
| log_home_distance_km | log1p of distance from home |
| is_foreign_country | 1 if country differs from home_country |
| hour_sin, hour_cos | cyclical hour of day in the account's home timezone |
| log_account_age_days | log1p of account age at occurred_at |
| ch_card_present, ch_card_online, ch_transfer, ch_ussd | one-hot channel |

Cold-start rules are written above (zscore, geo velocity, secs since
last) so the training and live paths agree exactly.

## 6. ScoredEvent (txn.scored, v=1)

txn_id, occurred_at, scored_at, account_id, amount_minor, currency,
merchant_id, merchant_category, channel, geo, features (the vector, for
debugging and the dashboard), rule_hits (list of code, severity,
detail), anomaly_score (float, higher is more anomalous, defined as the
negated sklearn score_samples), flagged (bool), flag_reasons (RULE
and/or MODEL), model_version, feature_schema_hash, rules_version,
score_latency_ms. No label, ever.

## 7. Ground truth

Scenario labels live only under `truth:{txn_id}` and in the evaluation
output. The scorer and the API never read them.
