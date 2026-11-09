# PortfolioPulse — Reviewer Demo Script

## Purpose
A 10–15 minute reproducible walkthrough that lets a reviewer inspect the backend behaviour rather than rely on claims.

## Before the demo
- Start the application using the documented Docker Compose instructions.
- Confirm `/health` and `/ready`.
- Open Swagger at `/docs`.
- Use only synthetic sample data and local demo credentials.
- Record the commit hash and date of the demo.
- If any step fails, record it; do not edit the result to look successful.

## Walkthrough
1. **Explain the domain (1 min):** organisation → versioned reporting template → period → company submission → review/decision → approved metrics.
2. **Authenticate (1 min):** sign in as the local demo admin and inspect the current user.
3. **Configure reporting (2 min):** create a template with revenue and expenses, then create a period tied to that template version.
4. **Register two synthetic companies (1 min):** use the Streamlit Companies page.
5. **Submit valid data (1 min):** upload a one-row CSV for Company A1 and confirm it is pending review.
6. **Submit invalid data (1 min):** upload Company A2 with negative revenue; inspect actionable validation errors.
7. **Correct and resubmit (1 min):** upload corrected values linked to the failed submission; confirm both records remain in history.
8. **Review and decide (2 min):** sign in as analyst to record reviews, then as admin to approve both submissions.
9. **Verify analytics and traceability (2 min):** reconcile approved-only portfolio totals and inspect submission events and audit history.
10. **Verify isolation (1 min):** run the synthetic cross-tenant API test; another organisation cannot read the companies or submissions.
11. **Discuss limitations (1 min):** synchronous processing, fixed supported metric types, no production users, and no formal security audit.

The automated scenario is `tests/test_reporting_lifecycle.py::test_complete_synthetic_reporting_lifecycle_is_tenant_scoped`. The PostgreSQL ingestion and tenant-constraint checks are in `tests/test_postgres_integration.py`. Live database evidence belongs in `docs/RELEASE_VERIFICATION.md`; a test file alone is not proof of a local or production run.

## Evidence capture
Capture dated screenshots or a short recording of:
- successful clean startup;
- health/readiness responses;
- login and current-user response;
- valid upload response;
- invalid upload response;
- analytics response;
- test command output;
- CI run URL and commit SHA, if CI has actually passed.

Do not publish access tokens, passwords, `.env`, database dumps or personal data.

## Reviewer feedback form
- What was clear?
- What was confusing?
- Which invariant or edge case was missing?
- Which API contract would you change?
- What would block adoption in a real organisation?
- Which claim in the README needs stronger evidence?
