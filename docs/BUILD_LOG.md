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
