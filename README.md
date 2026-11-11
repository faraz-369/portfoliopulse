# PortfolioPulse.,.

A standalone business-portfolio reporting platform demonstrating backend application engineering with FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, CSV ingestion, deterministic KPIs, JWT authentication, role-based access control, and a Streamlit client.

> **Project provenance:** PortfolioPulse is an independently built demonstration project. It is not NIC Faisalabad software, does not reproduce a proprietary system, and uses synthetic data only.

## Features
- Organisation-scoped users, companies, reporting periods, submissions and metrics.
- JWT login and Argon2 password hashing.
- Admin, analyst, viewer and company-bound submitter permissions.
- Organisation-scoped, versioned reporting templates bound to reporting periods.
- CSV validation with actionable row/column errors and retained invalid submissions.
- Submission review and approval lifecycle with analyst review, admin decisions and resubmission history.
- SHA-256 idempotent retry handling and PostgreSQL tenant-consistency constraints.
- Approval-gated Decimal analytics; unapproved, rejected and superseded submissions are excluded.
- Submission transition history, processing logs and audit records.
- Alembic migration, repeatable demo seed, sample CSVs.
- Responsive Streamlit workspace with organisation-aware navigation, a data-backed overview, company management, reporting configuration, validated submissions and review, approved-only analytics, processing and audit history, and account settings.
- Pytest suite, Ruff configuration, Docker Compose and GitHub Actions.

## Quick start (Windows + VS Code)
1. Install Docker Desktop and start it.
2. Open the project folder in VS Code.
3. Copy `.env.example` to `.env`.
4. In the VS Code terminal, run:

```powershell
docker compose up --build
```

The backend container waits for PostgreSQL and applies Alembic migrations on startup. It does **not** seed demo data automatically.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/ready
- Streamlit: http://localhost:8501

### Local demo accounts
These are local development/demo credentials only. Do not use them in production.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@portfoliopulse.example.com` | `ChangeMe123!` |
| Analyst | `analyst@portfoliopulse.example.com` | `ChangeMe123!` |
| Viewer | `viewer@portfoliopulse.example.com` | `ChangeMe123!` |

Demo data is created only by an explicit development command. With the stack running, opt in for that one command:

```powershell
docker compose exec -e ENABLE_DEMO_SEEDING=true backend python -m scripts.seed_demo_data
```

The seed is idempotent and preserves existing passwords. It also safely updates legacy `.local` demo email addresses in place, preserving IDs, organization associations, roles, activation states and password hashes. The local demo password defaults to `ChangeMe123!`; set `DEMO_PASSWORD` in the development `.env` before seeding to choose another. Demo seeding is rejected outside development and production settings reject both demo-seeding opt-in and `DEMO_PASSWORD`.

The checked-in Compose file and `.env.example` are for local development, not production deployment. Production must explicitly configure `ENVIRONMENT=production`, `SECRET_KEY` (at least 32 characters and not a development default), `DATABASE_URL` (PostgreSQL), and `CORS_ORIGINS` (comma-separated HTTPS origins). Production also rejects the local database password, SQLite URLs, demo credentials, and demo-seeding opt-in. The application validates these settings before creating the FastAPI app or database engine. Use a managed secret source and a production deployment configuration; none is provided in this project.

## Complete the reporting workflow
1. Sign in to Streamlit as the local demo admin.
2. In **Reporting workflow**, configure a reporting template and create a period that refers to that template version.
3. Upload a CSV for a registered company. The UI shows the expected columns for the period's immutable template version.
4. Review validation feedback; choose a failed submission when uploading a corrected file to preserve its resubmission link.
5. An analyst records a review note; an admin approves or rejects the reviewed submission with a reason.
6. Confirm only approved submissions appear in portfolio analytics and inspect the submission timeline and audit history.
7. Sign in to another organisation in tests to verify tenant isolation.

Template CSVs begin with `company_identifier,reporting_year,reporting_month`, followed by the selected template's metric keys in template order. The initial migrated/demo template includes:
`revenue,expenses,customer_count,new_customers,employee_count,cash_balance`

Invalid submissions are saved with status `validation_failed` and HTTP 422 plus structured errors. Corrected submissions create new history entries and do not overwrite earlier submissions. Portfolio analytics use only approved data, selecting each company's latest approved report; missing metric values remain `null`. Revenue/expenses/profit and new customers are flows; customer, employee, and cash balance are snapshots.

## Useful commands
```powershell
docker compose exec backend pytest -q
docker compose exec backend pytest --cov=app --cov-report=term-missing
docker compose exec backend ruff check .
docker compose exec backend alembic upgrade head
docker compose exec -e ENABLE_DEMO_SEEDING=true backend python -m scripts.seed_demo_data
```

### PostgreSQL integration tests
The normal suite uses in-memory SQLite. PostgreSQL integration tests require a dedicated database whose name ends in `_test`; they recreate tables only in that isolated database:
```powershell
docker compose exec db psql -U portfolio -d portfolio -c "CREATE DATABASE portfoliopulse_test;"
docker compose exec -e PORTFOLIOPULSE_TEST_DATABASE_URL=postgresql+psycopg://portfolio:portfolio@db:5432/portfoliopulse_test backend pytest -q tests/test_postgres_integration.py
```

## Non-Docker setup
Use Python 3.12+, install PostgreSQL, create a database, copy `.env.example` to `.env` in the project root, and configure its `DATABASE_URL` for the local PostgreSQL instance. From the project root, copy the file to the backend working directory and run:
```powershell
Copy-Item .env backend\.env
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
$env:ENABLE_DEMO_SEEDING = "true"
python -m scripts.seed_demo_data
$env:ENABLE_DEMO_SEEDING = "false"
uvicorn app.main:app --reload
```
In a second terminal:
```powershell
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## API overview
All endpoints are under `/api/v1`. See Swagger for schemas and interactive requests.
- Auth: `/auth/login`, `/auth/me`, `/auth/change-password`
- Companies: `/companies`
- Templates: `/reporting-templates`, `/reporting-templates/{id}/versions`
- Reporting periods: `/reporting-periods`
- Reports: `/reports/upload`, `/reports`, `/reports/{id}`, `/reports/{id}/errors`, `/reports/{id}/logs`, `/reports/{id}/events`, `/reports/{id}/review`, `/reports/{id}/decision`
- Analytics: `/analytics/companies/{id}/overview`, `/analytics/companies/{id}/trends`, `/analytics/portfolio/overview`
- Logs: `/audit-logs`, `/processing-logs`

## Tests
Tests use SQLite in-memory for fast isolated API/business tests; the optional PostgreSQL tests require a separate `_test` database. Neither test target uses the demo data database. Run `pytest -q` from `backend/`; PostgreSQL constraints can be exercised with the command above. The suite covers authentication, templates and version history, correction/review/approval, analytics gating, audit events, tenant isolation, and database-enforced relationships.

## Limitations
- Imports are synchronous and bounded by `MAX_UPLOAD_BYTES`.
- Refresh-token rotation, password reset email, MFA, advanced tenant provisioning, background queues and cloud deployment are not included.
- Streamlit provides template/period configuration, report upload/correction, review/decision, portfolio analytics, processing history and admin audit history.
- The app is a portfolio demonstration and has not undergone a professional security audit.
- The project does not claim real users, adoption, commercial outcomes or production deployment.

## Architecture
See `docs/architecture.md`, `docs/database_design.md`, `docs/data_processing.md`, `docs/security.md`, `docs/testing_strategy.md`, `docs/deployment.md` and `docs/engineering_decisions.md`.


## Product and engineering evidence pack

This repository also includes a product and evidence pack:
- `docs/PRODUCT_STRATEGY.md` — problem hypothesis, target users, workflow and scope.
- `docs/8_MONTH_ENGINEERING_ROADMAP.md` — an eight-month roadmap with evidence gates. This is a proposed plan, **not a claim that eight months have already been spent**.
- `docs/CLAIMS_AND_EVIDENCE.md` — maps professional claims to proof and explicitly identifies unsupported claims.
- `docs/ENGINEERING_DEFENSE.md` — technical questions and defensible answer frameworks.
- `docs/DEMO_AND_REVIEW_SCRIPT.md` — reproducible reviewer walkthrough.
- `docs/ENGINEERING_BACKLOG.md` — prioritised verification and product backlog.
- `docs/PERSONAL_CLAIM_LANGUAGE.md` — accurate portfolio and interview wording.

**Evidence standard:** a feature is not “verified” because code or a test file exists. Record the command, environment, commit and actual result. The eight-month roadmap is a future execution framework; do not represent it as completed history.

Project origin and professional-context boundaries are documented in [`docs/evidence/PROFESSIONAL_CONTEXT.md`](docs/evidence/PROFESSIONAL_CONTEXT.md). PortfolioPulse is an independent project with synthetic data; historical internship details and impact metrics remain unverified unless supported by approved evidence.

## Engineering correctness update

The implementation includes the following correctness changes:

- Reporting periods now use the actual last calendar day (including leap years).
- Password changes accept a validated JSON request body instead of URL query parameters.
- Successful login updates the user's `last_login_at` timestamp.
- CSV ingestion counts data records independently from validation-error count, normalises duplicate-row keys, ignores fully blank records, and flags short/malformed rows.
- All-invalid CSV submissions and validation errors are persisted and retrievable.
- Portfolio rollups use each company's latest report; company summaries distinguish cumulative flows from latest-period snapshots.
- Company trend output is ordered chronologically by reporting year and month.
- Regression tests cover leap-year month boundaries and the password-change flow.

Latest local verification (2026-11-10, Docker Compose/Python 3.12): 34 tests passed, including five PostgreSQL integration tests against the separate `portfoliopulse_test` database; Ruff passed; frontend Python syntax compilation passed; Alembic reached `0005_reporting_schema_alignment`, a fresh PostgreSQL migration/seed run succeeded twice, and `alembic check` found no schema drift. The live synthetic workflow created a template/period, validated a failure, corrected and resubmitted it, reviewed and approved two reports, and verified portfolio totals of 210.00 revenue, 80.00 expenses, and 130.00 profit. Live health/readiness/docs/Streamlit and all three demo logins with `/auth/me` were exercised; invalid password returned 401 and invalid email returned 422. These results are specific to this local workspace and do not establish a clean CI run or production readiness; see `docs/RELEASE_VERIFICATION.md`.


## What makes this project worth reviewing

PortfolioPulse is not presented as a generic CRUD dashboard or as a production-proven product. Its engineering thesis is a traceable portfolio-reporting workflow: tenant-scoped company records, periodic reporting, explainable CSV validation, financial metrics, and submission/audit history.

The signature review scenario is an end-to-end mixed-quality CSV submission followed by duplicate prevention, analytics verification, source traceability, and a cross-tenant access challenge. See [`docs/PRODUCT_DIFFERENTIATION.md`](docs/PRODUCT_DIFFERENTIATION.md) and [`docs/REVIEWER_CHALLENGE_PACK.md`](docs/REVIEWER_CHALLENGE_PACK.md).

### Proof, not adjectives

This repository separates implemented behaviour from tested behaviour, CI verification, external review, deployment, and adoption. See:
- [`docs/COMPETENCE_PROOF_STANDARD.md`](docs/COMPETENCE_PROOF_STANDARD.md)
- [`docs/AUTHORSHIP_AND_PROVENANCE.md`](docs/AUTHORSHIP_AND_PROVENANCE.md)
- [`docs/RELEASE_EVIDENCE_TEMPLATE.md`](docs/RELEASE_EVIDENCE_TEMPLATE.md)
- [`docs/EVIDENCE_LEDGER_TEMPLATE.csv`](docs/EVIDENCE_LEDGER_TEMPLATE.csv)
- [`docs/EXTERNAL_REVIEW_REQUEST.md`](docs/EXTERNAL_REVIEW_REQUEST.md)

**Important:** this project does not prove historical employment or eight months of NIC work. It is an independent project. Do not claim real customers, production use, external review, or eight months of elapsed development unless separate dated evidence supports those claims.
