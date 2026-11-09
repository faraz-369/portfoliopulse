# PortfolioPulse Product Demo Plan

## Purpose and claims

Demonstrate the existing backend-first reporting path and its current limitations using synthetic data. This is a software walkthrough, not evidence of customer adoption, validated demand, production readiness, investment analysis, or business impact.

## Demo roles

Use the local development demo accounts documented in the root README:

- **Admin:** configure a company and reporting period through Swagger.
- **Analyst:** upload the reporting CSV and inspect submission/error records.
- **Viewer:** inspect the resulting tenant-scoped summary and confirm read-only permissions.

These are demo roles, not real users. Do not publish passwords, access tokens, `.env`, or database contents.

## Environment and data

- Start with `docker compose up --build` in a disposable local development environment.
- Confirm `/health` and `/ready` and open `/docs` and Streamlit.
- Do not delete the persistent project database or use production data.
- The seed provides synthetic demo companies and 2025–2026 periods. The current seed assigns day 28 as every period end; call this out rather than using those dates as evidence of correct period boundaries.
- Existing sample CSVs are synthetic. `sample_data/valid/acme_jan_2026.csv` has one ACME-001 row: revenue 1,500,000.00; expenses 950,000.00; customers 250; new customers 18; employees 12; cash 450,000.00. The arithmetic profit for this one row is 550,000.00.
- `sample_data/invalid/mixed_errors.csv` has negative revenue and an unknown company but no valid row. Current ingestion rejects all-invalid files before storing row-level errors. Do not present this file as a working end-to-end validation-feedback demo.

## Walkthrough

1. **Explain the hypothesis (1 min):** teams may need consistent reporting; this has not been validated with customers.
2. **Check local services (1 min):** open health and readiness separately; explain that process liveness and DB readiness are different.
3. **Authenticate (1 min):** log in as the local admin and call `/api/v1/auth/me`. Never display or capture the returned token.
4. **Inspect portfolio setup (2 min):** list demo companies and periods. Note that setup is API/seed-based and there is no organization/user onboarding UI.
5. **Upload the valid sample once (2 min):** upload `sample_data/valid/acme_jan_2026.csv`. Expected in a fresh seeded database: one accepted metric for ACME-001, 2026-01; revenue 1,500,000.00; expenses 950,000.00; calculated arithmetic profit 550,000.00. Confirm the response actually returned these values/statuses before stating them.
6. **Inspect submission history (1 min):** call `/api/v1/reports`, `/api/v1/reports/{id}`, and `/api/v1/reports/{id}/logs`. Verify the submission and logs refer to the same organisation and upload; avoid asserting row-error behavior for the all-invalid fixture.
7. **Show duplicate-file behavior (1 min):** submit the exact same bytes again. Expected current behavior is HTTP 400 for duplicate checksum; capture the observed response.
8. **Show role boundary (1 min):** authenticate as viewer and attempt the upload. Expected current route dependency is 403; confirm before claiming. Read-only data should remain available.
9. **Show analytics and discuss limits (2 min):** retrieve company/portfolio views. Reconcile arithmetic for the single metric. Portfolio totals select each company's latest available report; clearly note that selected reporting periods may differ. Company flow totals are cumulative, while customer/employee/cash values are latest-period snapshots.
10. **Close with known gaps (1 min):** no company representative portal, no formal review lifecycle, no configurable templates, Ruff still has findings, and there is no verified production operation or customer research.

## Repeatability and safety

- A byte-identical upload is intentionally rejected. Do not expect the same file to create a second metric.
- Repeating the walkthrough against a persistent demo volume may encounter already-existing submissions/metrics; inspect actual state before interpreting results.
- Use a disposable local environment or a unique company-period fixture for repeatable test demonstrations. Do not remove the persistent volume without explicit authorisation.
- If an API response differs from the expected result, record it as a finding rather than editing data/code during the demo.

## Evidence to capture

- Date, environment/runtime version, and repository revision if available (the reviewed workspace was not a Git repository).
- `docker compose ps`, migration revision, and health/readiness responses.
- Redacted login identity and `/auth/me` role only; never token or password.
- Exact upload response, stored submission details, duplicate response, viewer denial, and analytics response.
- Full test and Ruff command output with failures preserved.
- Screenshots with synthetic values only. Avoid showing `.env`, tokens, passwords, private IPs, or database dumps.

## Reviewer questions

- Who requests and validates this information today?
- Which metrics recur across companies, and what units/currency/time basis are required?
- Is one file per company-period acceptable?
- Who may correct a submitted value, and must historical values remain visible?
- Which figure must reconcile with the source submission?
- What access, retention, and deployment controls would be necessary before real data could be used?
