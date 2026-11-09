# Claims & Evidence Ledger

Use this document before writing a CV bullet, LinkedIn post, portfolio claim or interview answer.

## Claim strength levels
- **Verified fact:** directly supported by a primary record or reproducible artifact.
- **Demonstrated capability:** independently reproducible in this repository, with tests or a working demo.
- **Reported but unverified:** remembered or estimated; do not present as a measured outcome.
- **Planned:** intended future work; never describe in past tense.
- **Not supported:** no adequate evidence; omit.

## PortfolioPulse claim map

| Proposed claim | Evidence needed | Current status |
|---|---|---|
| Built a FastAPI backend for portfolio reporting | Source code, API contract, reproducible run | Demonstrated locally; this workspace's Docker Compose runtime and API flows were verified |
| Designed relational persistence with SQLAlchemy and Alembic | Models, migration, clean database migration test | Local PostgreSQL is at migration head `0003_failed_context_nullable`; migration and seed rerun succeeded |
| Implemented CSV validation and partial acceptance | Processing code, fixtures, endpoint tests | Endpoint tests and persisted failed/partial upload paths pass in the local 21-test suite |
| Implemented authentication and role checks | Security code, auth/RBAC tests, negative tenant tests | Three live demo login and `/auth/me` flows pass; live negative credential validation was checked; broad cross-tenant/security assurance is not established |
| Implemented CI | Workflow file and successful hosted run | Workflow file exists; green hosted run not verified |
| Achieved 80% test coverage | Coverage report from executed suite | Not established; do not claim |
| Production deployment / real customers | Deployment record, customer permission, usage evidence | Not established; do not claim |
| Reduced reporting effort by X% | Baseline, measurement method, after-state, attribution | Not established; do not claim |
| Built PortfolioPulse at NIC | Dated NIC work records and institutional confirmation | Explicitly not claimed; this is an independent project |

## Historical eight-month experience: evidence checklist
For an internship or role, use:
- certificate or contract confirming organisation, title and dates;
- supervisor/manager confirmation where available;
- dated task records, tickets, reports or approved deliverables;
- specific responsibilities you personally performed;
- tools and systems you actually used;
- measurable outcomes only when the baseline and calculation are available;
- permission to share any artefacts or anonymised examples.

A certificate usually proves affiliation and dates; it does not automatically prove every technical responsibility or impact metric.

## Safe wording
- “During my internship, I worked on…” only for tasks you actually performed.
- “I reported an estimated…” only if you can explain how the estimate was calculated.
- “I independently built PortfolioPulse to demonstrate…” for this project.
- “The current repository includes…” when discussing code that exists but has not been run.
- “The test suite is designed to cover…” when tests exist but have not been executed.

## Do not use
- “Production-grade” without production evidence and operational validation.
- “Scalable” without a defined workload and performance tests.
- “Secure” as an absolute; describe specific controls and their test coverage.
- “80% coverage” without a generated coverage report.
- “Saved 12 hours/week” or “60% automation” without source data, baseline and attribution.
