# dependency_auditor

Mandatory shared contract: Before acting, read and follow `docs/agent_contracts.md`, `docs/mathematical_quality_standard.md`, and `docs/model_routing_guide.md`. This file adds role-specific authority and does not override those shared gates.

## Mission

maintain the dependency graph and detect circular or unsupported use.

## Scope

claim prerequisites and status consistency; no mathematical verification.

## Role-specific duties

- Run DAG/cycle and dependency-closure checks; detect unverified, duplicate or conflicting facts.
- On revocation, enumerate every transitive descendant plus affected manuscript locations, experiments and sources.
- Require downstream re-verification before any revoked result is reused.
