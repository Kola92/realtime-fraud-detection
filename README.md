# Real-Time Fraud Detection Service

Real-time fraud detection over a Redis Streams event pipeline. Every
transaction is scored by two independent signals, a rule engine and an
Isolation Forest anomaly model, and flagged transactions appear on a
live Angular dashboard over WebSockets.

**Status:** design phase. Architecture, data model and event contracts
are documented; no application code yet.

## Planned architecture

- **Producer:** seeded synthetic transaction generator (Python)
- **Event backbone:** Redis Streams with a consumer group
- **Scorer:** shared feature code, rule engine and Isolation Forest
- **API:** FastAPI, REST plus WebSocket fan-out
- **Dashboard:** Angular with SSR

## Documentation

- [docs/DECISIONS.md](docs/DECISIONS.md): architecture decision records
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md): event contracts and features
- [docs/BUILD_LOG.md](docs/BUILD_LOG.md): how it is being built

## A note on the data

All transactions are synthetic. Evaluation metrics demonstrate that the
pipeline works end to end, not that the model would catch real-world
fraud.
