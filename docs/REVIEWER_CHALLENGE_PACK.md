# Reviewer Challenge Pack

This is a set of reproducible challenges, not a claim that every challenge has passed.

## 1. Reproduce from a clean checkout
Record OS, Python, database version, commit SHA, exact setup commands, `ruff check .`, `pytest -q`, PostgreSQL migrations, Docker build and smoke-test output. A second person should be able to follow the same steps.

## 2. Tenant isolation
Create two organisations and users. Create company/report data in A, then authenticate as B and attempt reads, updates, deactivation, analytics, report-error and processing-log access using A identifiers. Pass only if no A data is returned or changed. UUID obscurity is not access control. Add regression tests for each route.

## 3. CSV adversarial inputs
Test UTF-8 BOM and invalid encoding; missing/reordered/duplicate/unexpected headers; extra/missing cells; blank lines; invalid, negative, NaN, Infinity and high-precision decimals; negative/fractional/huge counts; duplicate company-period rows; exact file re-upload; already-reported periods; oversized files. Record the exact outcome and persistence behaviour for each.

## 4. Authentication and authorisation
Test missing, malformed, expired and tampered JWTs; inactive users; wrong passwords; analyst access to admin-only operations; wrong current password; old/new password login after password change. Confirm 401/403 behaviour and ensure secrets/hashes do not leak.

## 5. Integrity and concurrency
Challenge uniqueness constraints, simultaneous uploads for one company-period, process failure during ingestion, duplicate simultaneous file submissions, and rollback semantics. Explain actual behaviour from code and tests. If a race exists, record it as a defect; do not claim concurrency safety.

## 6. Financial correctness
Test zero, large values, revenue below expenses, decimal rounding boundaries, and out-of-order months. Explain Decimal use, rounding policy, negative profit, and chronological trend ordering.

## 7. Operability
Determine whether `/health` is liveness or dependency readiness; test database outage handling; inspect logs for usefulness and sensitive data; document backup/restore; test migrations. Do not call a liveness check readiness.

## 8. Author defence
Without reading prepared answers, explain the user workflow, request-to-database flow, tenancy boundary, CSV validation/persistence, atomicity, one difficult bug, three trade-offs, two rejected alternatives, limitations, and what must change before real customer data is used.

## Review record
For every review capture date, commit SHA, reviewer role/name only with permission, environment, exact challenge, observed result, defect, issue/commit addressing it, and unresolved risk. “Looks good” is not a technical review.
