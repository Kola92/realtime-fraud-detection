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

---

## ADR-003: Redis Streams as the event backbone

**Status:** Accepted

**Problem solved:** A durable, replayable, consumer-group event log
between the generator, the scorer and the API, with no extra
infrastructure. Pub/Sub would drop messages whenever a consumer is down.

**Topology:** producer XADDs to `txn.raw`. A consumer group `scorers`
reads it (XREADGROUP), scores, writes `txn.scored` and XACKs. Each API
instance reads `txn.scored` with plain XREAD (no group) so every
instance sees every event and can broadcast to its own WebSocket
clients. After N failed deliveries a message moves to `txn.dead`.
Crashed consumers are recovered with XAUTOCLAIM.

**Traded away:** Kafka-class partitioning and retention. Streams are
memory-bound, so both streams are trimmed with MAXLEN. Delivery is
at-least-once, so the scorer must be idempotent (dedupe on txn_id).

**Ordering:** A group gives no ordering across consumers, and velocity
features depend on per-account order. v1 runs a single scorer consumer.
The scale path is sharding streams by hash(account_id) modulo N.

**What breaks if changed:** Pub/Sub loses events when a consumer is
down. Kafka is too heavy and not $0. Multiple unsharded consumers
corrupt velocity features silently.

---

## ADR-004: Angular with SSR (@angular/ssr) for the dashboard

**Status:** Accepted

**Problem solved:** Demonstrates Angular, my deepest production skill,
which Projects 1 to 3 did not show. RxJS fits a continuous stream: a
WebSocket Observable with retry and backoff, combineLatest to merge the
alert stream with aggregate stats, async pipe and OnPush change
detection to keep rendering cheap.

**Traded away:** SSR adds a Node server to deploy and gives little for
the live dashboard itself, since the WebSocket only exists in the
browser. Its real value is the app shell, a public landing or summary
view, and first paint. The article must say this honestly.

**What breaks if changed:** Browser-only APIs (WebSocket, window) must
be guarded with platform checks, otherwise the server render tries to
open a socket and fails. Hosting for an SSR Angular app on a free tier
is an open question, decided later in its own ADR.

**Flag:** Confirm the current Angular version and the @angular/ssr
setup at scaffold time.

---

## ADR-005: Rules and Isolation Forest as two separate signals

**Status:** Accepted

**Problem solved:** Rules catch known patterns and give reason codes,
which fraud and compliance teams require. Isolation Forest catches
unusual behaviour no rule anticipated.

**Design:** Every scored event carries both `rule_hits` (with severity)
and `anomaly_score`. An event is flagged if any rule of sufficient
severity fires OR the anomaly score passes a threshold. The threshold is
chosen from validation data (target alert rate and precision/recall on
the held-out labeled set), not guessed. The model sees the derived
features, never the rule outputs, to avoid redundancy and leakage. The
model trains unsupervised on mostly normal traffic, and we use the raw
score with our own threshold, not predict().

**Traded away:** Isolation Forest returns a score, not reasons. The
dashboard shows rule reason codes for rule hits and the anomaly score
for model hits. Surfacing top deviating features is a possible later
improvement.

**What breaks if changed:** A single blended score hides which signal
fired and kills explainability. Rules only misses novel fraud. Model
only is unexplainable. Evaluate each signal alone and combined
(ablation), which is also good article material.

---

## ADR-006: Event contract and time semantics

**Status:** Accepted

**Problem solved:** A versioned, validated contract between producer,
scorer and API, and windows that behave identically in live, replay and
training runs.

**Decision:** Each stream entry carries `v` and one JSON `payload`.
Pydantic validates strictly at the consumer: enums, bounded string
lengths, lat/lon ranges, amount bounds. Invalid events go to `txn.dead`
with a reason and never crash the scorer. All windows are computed from
`occurred_at` (event time), never the wall clock. Money is integer
minor units.

**Traded away:** Redis cannot filter inside a JSON payload. Out-of-order
events are not handled in v1: the producer emits in order per account,
and this is a documented limitation.

**What breaks if changed:** Wall-clock windows make replays and training
disagree with live scoring. Float money introduces rounding drift.
Skipping validation lets one malformed message poison the consumer
group.

---

## ADR-007: Features from prior state, with train/serve parity

**Status:** Accepted

**Problem solved:** Train/serve skew and within-event leakage.

**Decision:** Features are computed from state strictly before the
current event, and state is updated only after scoring. A single
`compute_features` function runs against a `StateStore` interface with
two implementations: in-memory (batch training and evaluation) and
Redis (live). A parity test feeds the same event sequence through both
and asserts identical vectors. The feature schema hash is stored in the
model artifact, and the scorer refuses to load a model whose hash does
not match. The scorer sees only bank-visible profile fields and learns
per-account baselines online.

**Traded away:** An abstraction layer and a second state implementation
to maintain. Slightly slower than hand-tuned Redis code.

**What breaks if changed:** Two separate feature implementations drift
silently. Counting the current event in its own window leaks signal.
Giving the scorer generator internals makes every metric meaningless.
