# Build Log

Teaching-style record of how the Real-Time Fraud Detection Service was
built, updated as work happens.

## Entry 1: Repo setup

Created the repo at ~/personal-projects/realtime-fraud-detection. The
first attempt lived under a folder with a space in its name, which
breaks venv scripts, CLI tools and Docker mounts in confusing ways, so
the repo was moved to a space-free path before any commit. Verified git
identity before committing, because this machine is employer-managed
and a wrong-author commit has happened before. First commit contains
only .gitignore and .gitattributes: secrets, generated data and model
artifacts are excluded, and LF line endings are enforced so shell
scripts and Dockerfiles survive Windows checkouts.

## Entry 2: Decisions before code

Locked the backend language and the synthetic data strategy before
writing application code. See ADR-001 and ADR-002 in DECISIONS.md.

## Entry 3: Event backbone, frontend and detection design

Documented ADR-003 to ADR-005: Redis Streams topology with a single
scorer consumer for ordering, Angular with SSR and the honest limits of
SSR on a live dashboard, and two independent fraud signals with
validation-derived thresholds. Still no application code.

## Entry 4: Data model and event contract

Wrote docs/DATA_MODEL.md and ADR-006 and ADR-007. The key lessons: use
event time for windows so replays match live runs, compute features from
prior state and update state afterwards, and share one feature function
across training and live scoring behind a StateStore interface with a
parity test. The scorer is kept blind to generator internals so the
evaluation stays honest.

## Entry 5: A currency bug caught on paper, then rules and scenarios

Reviewing the feature spec before writing code, we found that amount
features mixed currencies: USD 100 is 10,000 cents while NGN 100 is
10,000 kobo, so a raw amount_minor is not comparable across currencies.
Fixed with ADR-008 (static, versioned FX table, amount_ngn_minor) and a
DATA_MODEL amendment. This is the argument for schema review before
code: the bug would have shown up as odd model behaviour weeks later.
Also wrote RULES_AND_SCENARIOS.md: the rule catalog, fraud scenarios
each paired with a legitimate twin, and a time-split evaluation plan
with a rules/model/combined ablation.

## Entry 6: Python scaffold and core models

Installed Python 3.13 per-user on a locked-down laptop (3.12 no longer
ships Windows installers), scaffolded a src-layout package with pinned
dependencies captured by pip freeze. Windows ships no timezone database,
so tzdata is an explicit dependency; without it ZoneInfo fails on
Windows. Wrote the core Pydantic models with extra=forbid (a label field
on an event is a validation error, enforcing ADR-002), strict integer
money, timezone-aware UTC datetimes, immutable instances, and the static
FX table from ADR-008, all with unit tests.
