# Eight-Month Product & Engineering Roadmap

## Important interpretation
This is a **proposed eight-month development and validation roadmap**, not proof that eight months have already been spent building PortfolioPulse. Do not place the roadmap on a CV as completed experience. If work is completed over time, retain dated commits, issues, test reports, design decisions and review notes for each milestone.

The project should earn its duration through progressively deeper engineering evidence—not by adding features for their own sake.

## Month-by-month plan

| Month | Theme | Engineering work | Evidence required to mark complete |
|---|---|---|---|
| 1 | Discovery & domain modelling | Interview target users; map current reporting workflow; define domain terms, invariants, user stories and acceptance criteria; model organisation/company/period/submission/metric relationships | Interview notes with consent, problem brief, PRD, ERD, decision record, prioritised backlog |
| 2 | API and persistence foundations | Refine modular monolith boundaries; SQLAlchemy models; PostgreSQL constraints; Alembic migrations; API contracts; pagination and filtering | Reproducible migration from empty DB, schema review, OpenAPI contract, integration tests |
| 3 | Identity, tenancy & permissions | Authentication lifecycle; password hashing; token expiry; role permissions; tenant isolation; security threat model | Auth/RBAC test matrix, cross-tenant negative tests, threat model, dependency/security scan |
| 4 | Data ingestion & validation | CSV schema versioning; file-size/content checks; row validation; partial acceptance policy; duplicate handling; transaction boundaries | Valid/invalid/duplicate fixtures, deterministic validation tests, rollback tests, sample error report |
| 5 | Domain analytics & correctness | KPI definitions; decimal precision; missing-data semantics; period comparisons; portfolio aggregation; explainable calculation provenance | Formula specification, hand-calculated fixtures, edge-case tests, reproducible analytics outputs |
| 6 | Reliability & operability | Structured logs; audit trail; readiness checks; database failure behaviour; upload limits; idempotency; observability basics | Failure-injection tests, operational runbook, logs examples, recovery procedure, measured test coverage |
| 7 | Usability & external review | Thin reviewer UI; API documentation; demo scenarios; code review by another engineer; fix findings; usability sessions | Review comments, resolved issues, demo script, usability findings, before/after evidence |
| 8 | Release hardening & proof packaging | Reproducible Docker setup; CI; migration verification; release checklist; architecture walkthrough; limitations and next steps | Green CI run, tagged release, clean-install recording/screenshots, release notes, evidence ledger |

## Monthly gate
A month is complete only when:
1. the stated deliverable exists;
2. it is committed with traceable history;
3. acceptance criteria are testable;
4. test results are recorded accurately;
5. unresolved defects and limitations are documented;
6. a reviewer can reproduce the result.

## Evidence log template
For every meaningful work session or milestone, record:
- Date and commit hash:
- Problem being addressed:
- Options considered:
- Decision and rationale:
- Implementation files:
- Tests added/changed:
- Commands executed and exact results:
- Review feedback:
- Known limitations:
- What the evidence supports—and what it does not support:

## What makes the eight months credible?
Not elapsed time alone. Credibility comes from a visible progression: problem discovery → domain model → implementation → correctness → security → reliability → review → release. A large code dump without that trail does not prove eight months of engineering judgement.
