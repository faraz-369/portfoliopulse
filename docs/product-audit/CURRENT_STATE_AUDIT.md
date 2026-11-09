# Current State Audit

> **Baseline note:** the findings below describe the pre-correctness-sprint audit snapshot. See “Phase 0 follow-up” at the end for changes and verification performed afterward; do not treat superseded baseline findings as current behavior.
>
> The subsequent reporting-lifecycle sprint adds templates, submission review/decisions, PostgreSQL tenant constraints, and the Streamlit workflow. For current verified behavior and results, see [`RELEASE_VERIFICATION.md`](../RELEASE_VERIFICATION.md) and [`USER_WORKFLOWS.md`](USER_WORKFLOWS.md).

## Scope and evidence

Reviewed the FastAPI backend, SQLAlchemy models, migrations, processing code, Streamlit client, Compose and Dockerfiles, tests, CI workflow, README, and existing architecture/security/testing documentation. The repository has no Git metadata in the inspected workspace, so this report cannot identify a commit SHA or compare changes against a baseline.

Runtime observations were made against the local Compose stack on 2026-11-09:

- `docker compose ps`: PostgreSQL reported healthy; backend and frontend were running.
- `alembic current`: `0002_demo_email_example_domain (head)`.
- `/health`, `/ready`, `/docs`, and the Streamlit root returned HTTP 200.
- Backend tests: 16 passed, 1 failed. The failure is described under Verification.
- Backend `ruff check .`: 41 errors.

These observations describe this local environment only. They are not production-readiness evidence.

## Product maturity assessment

**Maturity: locally runnable engineering demonstrator / early prototype.** It contains a real relational schema, authentication, role checks, tenant filters, CSV validation and analytics. It does not yet demonstrate a reliable, complete reporting product: setup is mostly seeded/API-only, ingestion accepts a very narrow file shape, business feedback is incomplete for wholly invalid files, analytics do not define stock-versus-flow aggregation, and the advertised CI quality gates currently fail.

The application is a modular monolith: FastAPI routes and domain logic reside mainly in `backend/app/main.py` and `backend/app/processing.py`; SQLAlchemy models are in `backend/app/models.py`; Streamlit is a separate HTTP client.

## Capability classification

“Verified” below means verified only for the stated path and environment; it does not imply broad or production validation.

| Capability | Classification | Evidence and limits |
|---|---|---|
| Local Compose startup and API liveness/readiness | **Implemented and verified locally** | `docker-compose.yml`; observed services running and `/health` and `/ready` returned 200. Only PostgreSQL has a Compose healthcheck. |
| OpenAPI/Swagger | **Implemented and verified locally** | FastAPI app in `backend/app/main.py`; `/docs` returned 200. |
| Password authentication and JWT identity | **Implemented and verified for demo flow** | `LoginIn` in `backend/app/schemas.py`; `login`, `me` in `backend/app/main.py`; Argon2 and JWT helpers in `backend/app/security.py`; auth tests pass; live demo logins were previously observed returning 200. No throttling or token revocation is implemented. |
| Role checks and organisation-scoped queries | **Implemented but not adequately tested** | `require_roles` and route dependencies in `backend/app/security.py` and `backend/app/main.py`. Existing company test does not create a second organisation or test a foreign resource. |
| Company create/list/read/update/deactivate | **Implemented but not adequately tested** | Routes in `backend/app/main.py`. Only create and same-tenant read/not-found are covered. No company management UI exists. |
| Reporting-period create/list | **Partially implemented** | Routes exist in `backend/app/main.py`; creation computes calendar month ends, but `PeriodOut` in `backend/app/schemas.py` omits `start_date`/`end_date`, causing the existing response test to fail. The seed script hardcodes day 28 for all periods. |
| CSV schema and row validation | **Implemented but not adequately tested** | `parse_and_validate` in `backend/app/processing.py` checks exact headers, encoding, company, period, numeric ranges and some row duplicates. `backend/tests/test_processing.py` tests the header constant and upload authentication only, not these validation rules end to end. |
| Report ingestion and duplicate handling | **Partially implemented** | `ingest` in `backend/app/processing.py` enforces size/extension, checks SHA-256 and unique company-period metrics, and commits submission, metrics, and logs in one transaction. One file is restricted to one company and one period. A file with no valid rows raises HTTP 400 before a submission or detailed row errors are stored. Concurrent duplicate attempts can race between the check and database constraint. |
| Submission tracking, validation records, and processing logs | **Partially implemented** | `ReportSubmission` and `ProcessingLog` in `backend/app/models.py`; report endpoints in `backend/app/main.py`. No status transition workflow, correction/reprocessing, analyst review, or approval/rejection actions exist. |
| Audit logging | **Partially implemented** | `AuditLog` model and admin read endpoint exist; password changes and company creation write entries. Company update/deactivation and other administrative actions do not consistently create audit records. |
| Company and portfolio analytics | **Partially implemented** | Overview/trend routes in `backend/app/main.py` use `Decimal` values, but portfolio totals sum customer/employee snapshots across periods, and company `latest_customers` uses an unordered query. Metric definitions and aggregation semantics need correction and tests. |
| Streamlit client | **Partially implemented** | `frontend/app.py` offers login, overview, company list, CSV upload, and import history. It has no company/period setup, submission correction/review, or KPI drill-down interface. |
| Automated quality gates | **Implemented but failing** | `.github/workflows/ci.yml` runs Ruff and pytest. Current local full suite had 16 passed / 1 failed; `ruff check .` reported 41 errors. No green CI result was verified. |
| Configurable templates, user/org provisioning, exports, backups, cloud deployment | **Missing** | No corresponding implementation was found in the reviewed API, models, Compose setup, or client. |
| Self-service company reporting and approval workflow | **Documented as a future/product hypothesis, not implemented** | Product documents describe possible workflows, but no company-representative role or submission review transition exists in the code. |

## Implemented workflows traced

### Sign-in and authorised API request

`frontend/app.py` collects email/password and sends JSON through `frontend/api_client.py`. `LoginIn` applies Pydantic `EmailStr` validation. `login` checks the stored password and active flag, updates `last_login_at`, and returns an access token. `get_current_user` decodes the token, loads the user, and checks active status and organisation claim. Route dependencies enforce role lists and business routes generally filter on the authenticated user's `organization_id`.

The flow has no account invitation or recovery process, request throttling, refresh token, or logout token revocation. The UI login flow is present, but not every page or error path has UI-level automated coverage.

### Portfolio configuration and reporting

The demo seed creates one demo organisation, three demo users, companies, and periods. Outside the seed, only admins can create companies and periods through API routes. The company representative cannot create an account or submit directly. The analyst/admin uploads a CSV; `ingest` validates it and writes a submission, metrics, and processing logs in one database transaction if at least one valid row exists. A viewer can read tenant-scoped summaries and submission data. No user-facing workflow tracks report requests, due dates, review, approval, or resubmission.

## Important evidence-backed gaps

1. **Broken date response contract:** `PeriodOut` excludes date fields, while `test_reporting_period_uses_actual_calendar_month_end` expects them. Current test fails with `KeyError: 'start_date'`.
2. **Incorrect seeded period ends:** `backend/scripts/seed_demo_data.py` sets each reporting period's end to day 28, including months with 29, 30, or 31 days.
3. **Ambiguous analytics:** portfolio overview sums customer/employee snapshots over every period; company overview does not order records before selecting the last customer count.
4. **Incomplete validation feedback:** the provided `sample_data/invalid/mixed_errors.csv` contains no valid row. `ingest` rejects a no-valid-row file before returning/storing its structured errors, so this sample cannot demonstrate row-level error retrieval through a created submission.
5. **Thin automated coverage:** no end-to-end import or cross-organisation isolation tests exist, and the full suite is not green.
6. **Failing static gate:** 41 current Ruff findings include unused imports and compressed one-line statements across app, migrations, processing, and tests.
7. **Development-oriented operations:** Compose has a persistent database volume but no backup/restore procedure, backend/frontend healthchecks, or deployment hardening.
8. **Stale evidence records:** `docs/RELEASE_VERIFICATION.md` still says dependencies, tests, PostgreSQL, and Docker were not run/available; `docs/CLAIMS_AND_EVIDENCE.md` likewise says runtime, migration, and full test verification remain outstanding. Those statements predate the local Compose/test observations above and must not be used as current evidence without updating them. Conversely, this audit's local results do not prove a clean checkout, green CI, or production readiness.
9. **Documentation drift:** `docs/api_reference.md` does not list every route present in `backend/app/main.py` (including organization identity, password change, and processing logs). Product documentation describes planned administrator organisation setup, but no corresponding provisioning API exists.

## Evidence sources

- API and permissions: [backend/app/main.py](../../backend/app/main.py), [backend/app/security.py](../../backend/app/security.py), [backend/app/schemas.py](../../backend/app/schemas.py)
- Domain and persistence: [backend/app/models.py](../../backend/app/models.py), [backend/app/db/session.py](../../backend/app/db/session.py), [backend/alembic/versions/0001_initial.py](../../backend/alembic/versions/0001_initial.py)
- Processing and seed: [backend/app/processing.py](../../backend/app/processing.py), [backend/scripts/seed_demo_data.py](../../backend/scripts/seed_demo_data.py)
- Client and operations: [frontend/app.py](../../frontend/app.py), [frontend/api_client.py](../../frontend/api_client.py), [docker-compose.yml](../../docker-compose.yml), [backend/Dockerfile](../../backend/Dockerfile), [frontend/Dockerfile](../../frontend/Dockerfile)
- Tests and CI: [backend/tests](../../backend/tests), [.github/workflows/ci.yml](../../.github/workflows/ci.yml)
- Existing product context: [docs/PRODUCT_STRATEGY.md](../PRODUCT_STRATEGY.md), [docs/PRODUCT_DIFFERENTIATION.md](../PRODUCT_DIFFERENTIATION.md), [docs/security.md](../security.md), [docs/testing_strategy.md](../testing_strategy.md)

## Phase 0 follow-up

The correctness sprint has since updated the reporting-period response and calendar month-end seeding; defined flow/snapshot semantics; selected each company's latest report for portfolio rollups and exposed period coverage; and persisted fully rejected uploads with retrievable validation logs and a structured HTTP 422 response. Regression tests cover these paths, partial acceptance, duplicate uploads, viewer upload denial, seeded month ends, and email-migration preservation/idempotence. A separate synthetic second-tenant test fixture now exercises cross-organisation list filtering, foreign-resource reads/updates/deletes, upload company resolution, analytics, submissions, and log routes.

Verification in the current workspace: backend pytest reports **25 passed**; Ruff passes; PostgreSQL reports migration head `0003_failed_context_nullable`; Docker Compose backend, database, and frontend are running; `/health`, `/ready`, `/docs`, and Streamlit returned HTTP 200; live admin/analyst/viewer login and `/auth/me` succeeded, while bad password/unknown user returned 401 and invalid email returned 422. The tenant tests use isolated SQLite and synthetic data; they do not prove every possible tenant boundary or PostgreSQL constraint behavior. This is local evidence only, not a clean hosted-CI result or production-readiness claim.
