# Release verification protocol

This document defines the evidence required before describing PortfolioPulse as a verified release. A command listed here is a required check, not evidence that it has already passed.

## 1. Reproducible environment

From the repository root:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

Record the Python version, operating system, dependency installation output, and commit SHA.

## 2. Static checks and automated tests

```bash
ruff check backend
python -m compileall -q backend/app backend/tests
cd backend
python -m pytest -q --disable-warnings --maxfail=1
python -m pytest --cov=app --cov-report=term-missing
```

Evidence to retain: full command, exit code, date, commit SHA, test count, failure output (if any), and coverage output. Never report a test as passing if it was skipped, blocked, or not run.

## 3. Database and migration checks

With PostgreSQL available and `DATABASE_URL` configured:

```bash
cd backend
alembic upgrade head
alembic current
alembic check
```

Run the API against the migrated database and verify `/health` and `/ready` separately. `/health` is process liveness; `/ready` verifies database connectivity.

## 4. Container checks

From repository root:

```bash
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --no-color
```

Verify API readiness and frontend-to-API connectivity. Save logs and redact credentials before sharing evidence.

## 5. Required manual acceptance scenarios

- Unauthenticated API requests are rejected.
- A viewer cannot perform admin writes or upload reports.
- Company submitters can access only their bound company and their own unassociated failed uploads.
- An organisation cannot retrieve another organisation's companies, submissions, metrics, or logs.
- Identical file retries are idempotent and do not expose another company's submission.
- CSV validation reports invalid values, malformed rows, extra columns, duplicate rows, and unknown company identifiers.
- Corrected submissions link to prior submissions without overwriting them.
- Review is required before admin approval/rejection; invalid transitions are rejected.
- Only approved metrics contribute to company and portfolio analytics; superseded/rejected data is excluded.
- Template versions remain bound to historical reporting periods.
- February ends on February 28 in a common year and February 29 in a leap year; 30- and 31-day months are also correct.
- Trend results are chronological even when records are inserted out of order.
- Audit and processing logs are scoped to the authenticated organisation and submission transitions are traceable.
- Password change requires the current password and a new password meeting the minimum length.

## 6. Release evidence record

Latest observed verification in this workspace (2026-11-10, local Windows Docker Compose):

| Field | Value |
|---|---|
| Date/time (with timezone) | 2026-11-10 00:49 +05:00 |
| Commit SHA | Unavailable; workspace has no Git metadata |
| Environment / Python | Windows host; Docker Compose; backend image uses Python 3.12 |
| Dependency install | Backend and frontend Docker images built; dependency layers were cached |
| Ruff | Passed: `docker compose run --rm --no-deps --entrypoint ruff backend check .` |
| Frontend syntax | Passed: `py_compile.compile('app.py', doraise=True)` in the built frontend image |
| Pytest | Passed: 34 tests, 1 third-party Starlette deprecation warning; no skipped tests in the final run |
| PostgreSQL integration | Five tests passed against isolated `portfoliopulse_test`; covered tenant foreign keys, template/period scope, submission/metric scope, approval uniqueness, rollback, and real PostgreSQL ingestion |
| PostgreSQL migration | Passed: `alembic upgrade head` reached `0005_reporting_schema_alignment`; `alembic check` reported no schema drift; startup reran migration and seed successfully |
| Fresh database bootstrap | Passed: full Alembic chain reached head on a separate empty PostgreSQL database; the demo seed ran twice and remained consistent |
| Docker build / compose | Passed: backend/frontend running; PostgreSQL healthy; existing volume retained |
| Manual API acceptance | `/health`, `/ready`, `/docs`, and Streamlit returned HTTP 200; all three demo login and `/auth/me` flows passed; invalid password returned 401 and invalid email returned 422 |
| Live synthetic workflow | Passed against the running API/PostgreSQL: template/period configured; A1 valid; A2 invalid, corrected, and resubmitted; analyst reviewed both; admin approved both; analytics returned 210.00 revenue, 80.00 expenses, and 130.00 profit; five state events were verified |
| Streamlit UI | Browser sign-in succeeded and the reporting workflow, template setup, and submission review controls rendered |
| Reviewer | Not recorded |

These results apply only to this local workspace; no hosted CI, clean checkout, exhaustive authorization matrix, or production readiness is established. The integration database is separate from the application database. Update this record with a new run rather than treating it as permanent evidence.

## 7. Definition of release-ready

A release is eligible to be called *verified for the tested environment* only after all applicable automated checks, migration checks, container checks, and manual acceptance scenarios pass on a recorded commit. This does not by itself establish production readiness, security certification, external adoption, or customer impact.
