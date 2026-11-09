# Architecture Decisions and Questions

## Current architecture

PortfolioPulse is a single-deployable modular monolith:

```text
Streamlit client -> FastAPI (/api/v1) -> dependencies/auth -> SQLAlchemy -> PostgreSQL
                                             |
                                             +-> synchronous CSV validation/ingestion
                                             +-> portfolio/company analytics
```

The API is the only frontend data path. `backend/app/main.py` owns HTTP routes and much of the use-case logic; `backend/app/processing.py` owns CSV parsing plus persistence; `backend/app/models.py` owns SQLAlchemy models. Alembic migrations live under `backend/alembic`. Compose supplies PostgreSQL, backend, and Streamlit.

## Existing choices and assessment

| Choice | Current reason/benefit | Assessment |
|---|---|---|
| Modular monolith | One local deployable with straightforward SQL transactions. | Appropriate for current scale; do not split into services absent measured need. |
| FastAPI + Pydantic | Request validation and generated OpenAPI. | Appropriate; response contracts and error envelopes need consistency. |
| PostgreSQL + SQLAlchemy | Relational integrity, tenant data, decimal values, transactions. | Appropriate; add tenant-aware constraints and integration coverage. |
| Synchronous bounded upload | Simpler local flow and a configured upload limit. | Appropriate for small MVP files until measured latency/throughput requires a queue. |
| Fixed CSV schema | Explainable first version and simple validation. | Appropriate only if product owner confirms one common schema; do not add configuration preemptively. |
| SQLite test fixture | Fast isolated tests. | Useful for units, insufficient for migration, concurrency, and PostgreSQL-specific integration confidence. |
| Streamlit client | Minimal review/demo interface over HTTP. | Appropriate for demonstrator; not sufficient proof of external-user experience. |

## Architectural weaknesses grounded in current code

The items below are the original audit baseline. The Phase 0 follow-up has since added stored error results for all-invalid uploads and explicit KPI semantics, but does not address the remaining architectural items.

1. Route and business responsibilities are concentrated in `main.py`; errors, response contracts, and permissions are harder to standardise as routes grow.
2. Ingestion validates and persists in a single procedural function; all-invalid results are now persisted, but the parsing and persistence responsibilities remain coupled.
3. Tenant isolation is largely enforced through query filters rather than composite database constraints for related records.
4. `ReportSubmission` structurally represents one company-period, while parser/design language suggests batch ingestion.
5. Initial migration `0001_initial.py` calls current `Base.metadata.create_all` rather than recording a frozen historical schema.
6. KPI semantics are now documented: portfolio totals use each company's latest report, while company flow totals remain cumulative. Reports from different companies may still represent different periods.
7. The test strategy uses SQLite only for API/business tests; local tests and Ruff pass, but hosted CI was not verified.

## Recommended changes (decision-neutral)

- Keep the monolith and existing stack.
- First establish API/domain contracts for period bounds, invalid submission handling, metric units, and KPI aggregation.
- Add explicit tests before extracting code; then separate small use-case/service functions only where tests demonstrate a clear boundary.
- Keep request/response schemas explicit and add consistent error types without leaking row data or secrets.
- Treat database unique constraints as authoritative and convert constraint conflicts to deliberate HTTP outcomes.
- Add PostgreSQL integration tests for migration, tenant constraints, and concurrent duplicate writes.
- Keep uploads synchronous while size/time measurements remain within explicit limits; add a queue only if observed workload justifies it.
- Adopt template versioning and immutable submission revisions only after the product owner selects required correction/audit semantics.

## Decisions requiring human approval before implementation

| Decision | Options and consequence |
|---|---|
| Primary workflow | Staff analyst uploads on a company's behalf (fits current code) vs company-representative self-service (requires users, invitations, scoped company membership and a submission UI). |
| File granularity | Keep one company-period per file for simplest traceability vs accept many company-period rows per submission (requires submission-to-many periods/companies and row-level results). |
| All-invalid file behavior | **Selected:** persist an attempted submission with errors and return HTTP 422 containing the stored submission ID and structured errors. This affects audit semantics, retry behavior, and response contract. |
| Corrections and approval | Overwrite the same company-period, create immutable revisions, or add explicit approve/reject state transitions. This affects historical analytics and audit requirements. |
| KPI definitions | **Selected for current implementation:** revenue/expenses/new customers are flows; customer/employee/cash are period-end snapshots; portfolio rollups use each company's latest report and expose period coverage. Currency selection remains unspecified. |
| Tenant membership | One user belongs to exactly one organisation (current model) vs users can access multiple tenants. |
| Data governance | Retention, deletion, backup, export, privacy classification, and permitted synthetic/demo values. |
| Deployment target | Local-only portfolio demonstrator vs a named hosting environment with a specific security and operating model. |

No decision above should be encoded as a broad architecture rewrite before the user or product owner confirms the required behavior.
