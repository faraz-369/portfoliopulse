# Engineering Gap Analysis

> **Baseline note:** selected Phase 0 issues described below have been resolved in the current workspace: period bounds, all-invalid upload persistence, and flow/snapshot aggregation. See [the current-state follow-up](CURRENT_STATE_AUDIT.md#phase-0-follow-up). Other gaps remain as originally assessed.

## API design

### Strengths

- FastAPI publishes an OpenAPI document and routes are namespaced under `/api/v1`.
- Pydantic request models validate login, company fields, and reporting-period inputs.
- Common outcomes use meaningful HTTP classes: 401 authentication failure, 403 role denial, 404 tenant-scoped missing resource, 409 duplicate setup, 400 processing failure, and 422 request validation.
- Company listing supports filtering and bounded limit/offset.

### Gaps

- Route definitions and most business logic live together in `backend/app/main.py`; response shapes are inconsistent dictionaries, ORM objects, and response models.
- Error responses are not a single documented envelope. Exception handling is inconsistent; `ready` masks all database exceptions as generic 503 without logging details.
- Reports and logs return at most 100 records without pagination metadata; report listing has no offset/filter.
- `PeriodOut` now exposes calendar date bounds; broader response consistency remains.
- Company create performs a pre-check, but `uq_company_org_slug` is the authoritative constraint; a concurrent duplicate can surface as an unhandled integrity error.
- A business-level error maps to HTTP 400 regardless of whether the request is malformed, conflicts with prior data, or is otherwise unprocessable.

## Database quality

### Strengths

- PostgreSQL/SQLAlchemy use foreign keys, tenant identifiers, named uniqueness constraints, numeric financial columns, and non-negative metric checks in `backend/app/models.py`.
- SQLAlchemy parameterisation is used for application queries; no string-built SQL injection path was identified in reviewed routes.
- The submission write path groups metrics and logs in a transaction and rolls back on persistence exceptions.
- A persistent PostgreSQL volume is declared in Compose.

### Gaps and risks

- Most tenant isolation is enforced by application filters, not composite database constraints tying a metric's company and period to the same organisation. A bad internal write could create cross-tenant references.
- `User.role`, statuses, and period bounds have no database enum/check constraints; there is no explicit constraint `start_date <= end_date`.
- Initial migration `0001_initial.py` calls `Base.metadata.create_all`; that migration's schema is not a frozen explicit DDL snapshot and depends on imported model metadata.
- Reporting-period seed dates now use actual calendar month ends, including leap years.
- `ReportSubmission` represents one company and period, and `ingest` rejects multiple company-period values in one file. This is narrower than a generic portfolio batch import.
- Duplicate check then insert is race-prone; the database unique constraint prevents duplicate state but the losing request does not translate integrity failure into a stable API response.
- Retention, privacy classification, deletion policy, backup, restore, and data migration procedures are not implemented.

## Authentication and authorisation

### Implemented

- `backend/app/security.py` hashes passwords with `pwdlib`'s recommended Argon2 configuration.
- JWTs are HS256 signed and include expiry, subject, organisation, and role claims.
- Authentication loads current user state from the database, rejects inactive users, and checks the token organisation against the current database user.
- Business routes generally scope reads to `user.organization_id`; selected writes use `require_roles`.
- Login schema uses `EmailStr`; malformed email is not accepted as a plain string.

### Gaps / risks

- No login rate limit, lockout, abuse detection, refresh-token rotation, revocation, MFA, password reset, or session inventory.
- `Settings.secret_key` has an unsafe development fallback; `.env.example` explicitly uses a placeholder requiring replacement. A deployment that omits a strong secret would have predictable signing material. This is a confirmed unsafe default, not evidence that the current local secret is exposed.
- Compose defines simple database credentials in the Compose file and is suitable only as a local demonstration unless replaced through a deliberate deployment configuration.
- RBAC and cross-tenant isolation have little automated coverage; foreign-resource tests are missing for submissions, analytics, and logs.
- Roles are stored as unrestricted strings; future role additions or typos can create undefined permission behavior.
- No confirmed SQL injection or authentication bypass was identified in the inspected request paths. This is a code-inspection observation, not a security certification.

## Data processing and business correctness

### Implemented

- UTF-8/UTF-8-BOM decoding; exact header validation; blank and malformed row handling.
- `Decimal` for monetary input; finite and nonnegative checks; integer count checks; a `new_customers <= customer_count` rule.
- Company/period lookup is tenant-scoped.
- File checksum and company-period uniqueness guards.
- Structured validation results and transactional metric/submission/log writes.
- A configured byte limit and `.csv` extension check.

### Important gaps

- CSV parsing and processing have few direct tests; existing `test_processing.py` checks the column constant and unauthenticated upload only.
- An all-invalid upload is now persisted with structured errors; file-level size/extension/byte-identical duplicate rejections still occur before submission creation.
- A 100%-valid file can only represent a single row for one company-period because repeated company-period keys are duplicates. Multiple-company or multiple-period valid rows are rejected.
- `invalid_rows` is set to the number of validation/duplicate issues, not necessarily distinct invalid source rows. The name could be misunderstood.
- File-level SHA-256 protects byte-identical repetition, not semantically equivalent files with different whitespace/order.
- Check-then-write concurrency handling is incomplete and no retry is defined.
- No persisted input snapshot/object reference or processing version exists, limiting exact reproducibility and reprocessing.
- Data quality rules, requiredness, units, currency, reporting period semantics, and rounding policy are fixed in code or unspecified.
- Portfolio aggregation now uses each company's latest report and exposes period coverage; company flows are cumulative while customer/employee/cash values are latest-period snapshots.
- No missing-submission/denominator model exists; an absent report may be confused with zero.

## Software quality

- Separation is partial: database models, settings, and security are separate modules, but the API router and business use cases are concentrated in `main.py`; parsing and persistence share one module.
- Function signatures in route and processing code are frequently untyped or under-typed; most files use compressed statements that reduce readability.
- `ruff check .` passes in the current backend container. Hosted CI was not verified.
- Backend and frontend dependencies are pinned, but no lockfile, dependency vulnerability scan, or image digest policy was observed.
- Error handling sometimes catches broad `Exception` (for example JWT decode handling and readiness) and removes diagnostic context; operational logging is minimal.
- The tests use SQLAlchemy SQLite in-memory fixtures; they are isolated from the Compose demo database, but do not cover PostgreSQL-specific behavior, concurrency, or migrations.

## Testing gaps and strategy

### Observed current coverage

The suite has tests for health, demo authentication and `/auth/me`, one company create/read/not-found flow, password change, CSV header constant, upload authentication, and Decimal arithmetic. The added demo-account migration tests cover idempotency, preservation, conflict rejection, and seed behavior.

On 2026-11-09, `docker compose exec -T backend pytest -q` returned **16 passed, 1 failed**. `test_reporting_period_uses_actual_calendar_month_end` fails with `KeyError: 'start_date'` because `PeriodOut` omits that field. In the same environment, `docker compose exec -T backend ruff check .` returned **41 errors**. These are actual local observations, not inferred CI results.

### Recommended test layers

1. **Unit:** CSV parser rules; decimal precision and rounding; date boundaries; KPI definitions; duplicate-key semantics.
2. **API integration on isolated PostgreSQL:** migrations from empty DB; role matrix; cross-organisation access for every object; report status/error contracts; transaction rollback; concurrent duplicate upload; uniqueness/error translation.
3. **Frontend contract:** request JSON, bearer header behavior, 401/422 messaging, and backend-unavailable messaging without exposing tokens/passwords.
4. **End-to-end Compose:** clean documented startup, admin setup, analyst upload, report/error inspection, viewer analytics, repeat upload, service health, and teardown of only a disposable test stack.
5. **CI gates:** clean Ruff, deterministic unit/integration suites, migration check, and a stable pinned environment; publish test reports but do not assert unmeasured coverage.

## Security review notes

Confirmed code-level safeguards include Pydantic validation, Argon2, expiring signed tokens, ORM queries, upload size/extension checks, and tenant filters in primary query paths. Confirmed security shortcomings are missing brute-force protections and unsafe secret defaults for non-local deployment. Potential risks requiring tests/review include inconsistent tenant references at the database layer, duplicate-write races, and the effect of stored CSV validation values in logs. No formal penetration test or external security review is evidenced.

## Reliability and operations

### Current local setup

- Docker Compose includes PostgreSQL 16, backend, frontend, and a named persistent volume.
- Database health uses `pg_isready`; backend starts after database health, runs Alembic then the seed, and launches Uvicorn.
- `/health` checks process liveness; `/ready` executes `SELECT 1`.
- The local Compose stack, migrations, and the four public URLs were checked during this audit and returned successfully.

### Operational gaps

- Backend/frontend Compose healthchecks are absent; frontend dependency uses start order rather than health.
- Migration and seed run inside the API container's startup command; multiple replicas could race these operations.
- No migration rollback plan, backup/restore check, alerting, metrics, trace IDs, structured application logs, or operational runbook.
- No production deployment target, TLS/reverse proxy, secret manager, resource policy, or persistence/retention plan exists.
- `docker compose up --build` and `.env.example` help local onboarding, but not production operation.
- CI runs only Ruff and pytest. Both gates currently fail locally, and no green CI run was verified.

## Classification of security/operational statements

- **Confirmed safeguards:** Argon2 helper, token expiry, role dependencies, tenant filters in relevant business queries, SQLAlchemy parameterisation, request schema validation.
- **Confirmed unsafe defaults/omissions:** predictable fallback secret in code, placeholder secret in example environment, simple Compose database credentials, no rate limiting, no backup/restore automation.
- **Potential risks, not confirmed exploits:** check-then-insert races; tenant-inconsistent foreign-key data if written outside API; sensitive data retention in validation log values; production exposure if development Compose settings are reused.
- **Not established:** exploitation, real-world customer-data exposure, production deployment, or a full security audit.
