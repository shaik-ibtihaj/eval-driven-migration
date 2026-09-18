# Evaluation-Driven Software Migration

This repository provides a benchmark for migrating a legacy Flask order-management backend to FastAPI while continuously measuring behavioral compatibility, quality, safety, and performance.

## Repository layout

- `apps/` contains the legacy application and the migrated implementation. Keeping both versions side by side supports controlled comparison throughout the migration.
- `harness/` contains the evaluation workflow: orchestration, agent definitions, model adapters, context construction, permission controls, and resumable checkpoints.
- `evaluator/` contains the evaluation suites and mechanisms, including frozen regression tests, differential checks, property tests, mutation testing, performance analysis, security checks, and architectural validation.
- `contracts/` stores behavior discovered from the legacy system, normalized contract representations, and contracts formally accepted for the migrated system.
- `experiments/` contains repeatable task sets, model configurations, and the policy used to decide whether an evaluation run passes its quality gates.
- `evidence/` stores traces, counterexamples, evaluation run artifacts, and reports produced during migration work.
- `infrastructure/` contains supporting Docker and database assets needed to run the applications and evaluation environment.

## Stage 2 commands

Copy `.env.example` to `.env` if local overrides are needed, then use `make start` to build and start PostgreSQL and the legacy API. Run `make reset` to rebuild deterministic database state, `make snapshot` to print it, `make test` for the PostgreSQL-backed suite, and `make stop` to stop services. `make setup`, `make test-unit`, `make lint`, and `make format-check` run the corresponding local `uv` workflows.

## Current status

Stage 1's authoritative contract is in [`docs/benchmark-specification.md`](docs/benchmark-specification.md). Stage 2 adds only the runnable Flask/PostgreSQL foundation, deterministic seed and payment mock, `/health`, and focused tests. The five business endpoints, FastAPI migration, agents, and evaluators have not been started.
