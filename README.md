# Evaluation-Driven Software Migration

This repository provides a minimal foundation for migrating a software system while continuously measuring behavioral compatibility, quality, safety, and performance. The project is intentionally limited to scaffolding at this stage; application logic, evaluation implementations, and infrastructure configuration will be added as the migration evolves.

## Repository layout

- `apps/` contains the legacy application and the migrated implementation. Keeping both versions side by side supports controlled comparison throughout the migration.
- `harness/` contains the evaluation workflow: orchestration, agent definitions, model adapters, context construction, permission controls, and resumable checkpoints.
- `evaluator/` contains the evaluation suites and mechanisms, including frozen regression tests, differential checks, property tests, mutation testing, performance analysis, security checks, and architectural validation.
- `contracts/` stores behavior discovered from the legacy system, normalized contract representations, and contracts formally accepted for the migrated system.
- `experiments/` contains repeatable task sets, model configurations, and the policy used to decide whether an evaluation run passes its quality gates.
- `evidence/` stores traces, counterexamples, evaluation run artifacts, and reports produced during migration work.
- `infrastructure/` contains supporting Docker and database assets needed to run the applications and evaluation environment.

## Initial commands

Run `make help` to list the placeholder workflow targets. The `test`, `evaluate`, and `clean` targets are intentionally non-operative until their corresponding tooling is introduced.

## Current status

Only the repository structure and minimal configuration placeholders are present. No application or migration logic has been implemented.
