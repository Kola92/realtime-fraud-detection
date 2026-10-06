# Architecture Decision Records

Every ADR answers three questions: what problem it solves, what was
traded away, and what breaks if it changes.

---

## ADR-001: Backend is full Python/FastAPI, no Node + ML sidecar

**Status:** Accepted

**Problem solved:** The Isolation Forest model must sit in the scoring
hot path. scikit-learn is Python-only in practice. One language means
one shared `core` package for feature definitions, used identically by
training and live scoring, which prevents train/serve skew.

**Traded away:** Speed of development in my strongest language (JS).
Also forgoes a polyglot microservice story, which would add a network
hop per score, a second runtime and a second deploy unit on a $0 budget
for no functional gain.

**What breaks if changed:** A Node API plus Python scorer needs an RPC
call per transaction and two copies of the feature logic. Drift between
the copies silently degrades model quality.

**Shape:** One repo, three entrypoints sharing `core/`: producer
(synthetic generator, XADD to txn.raw), scorer (consumer-group worker,
features + rules + model, writes txn.scored), api (FastAPI REST,
Swagger, WebSocket fan-out).

**Flags:** Pin the scikit-learn version (joblib artifacts break across
versions). Only load self-trained model artifacts (pickle executes
code). Check Redis host command limits and free-tier sleep behaviour
before choosing hosting; the generator needs a rate-controlled demo
mode.

---

## ADR-002: Synthetic data from a seeded, profile-based generator

**Status:** Accepted

**Problem solved:** Realistic, reproducible transaction data for
training, evaluation and a replayable live demo, with no dependency on
any other project.

**Design:** A population of synthetic accounts, each with a profile
(home city, lognormal amount distribution, active hours, usual devices
and merchants, transaction rate). Normal traffic samples from the
profile. Fraud scenarios injected at roughly 1 percent: account
takeover, card testing, impossible travel, velocity burst, account
drain. Hard negatives included (legitimate travel, salary-day
transfers, new-device upgrades). Money stored as integer minor units.
Account profile data lives in a profile store, not on the event.
Derived features (velocity, z-score, geo velocity, new-device flags,
cyclical hour encoding) are computed at score time from Redis state.

**Ground truth:** Scenario labels are stored in a separate hash keyed by
txn_id, never in the event payload. Used only for evaluation.

**Traded away:** Realism. Metrics on synthetic data prove the pipeline
works, not real-world fraud efficacy. This is stated plainly in the
README and the article.

**What breaks if changed:** Labels in the payload allow leakage. No hard
negatives makes metrics meaningless. An unseeded generator makes bugs
and demos unreproducible.
