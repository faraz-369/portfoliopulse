# Engineering change log

## 2026-11-08 — Correctness and evidence hardening

### Changed
- Reporting-period end dates now use the calendar's actual final day, including leap years.
- Password-change input is a typed JSON schema with bounded lengths and a 12-character minimum for the new password.
- Successful login records `last_login_at`.
- CSV row accounting now counts data records independently of the number of validation messages.
- CSV duplicate-row keys are whitespace-normalised; empty lines are ignored; short and over-wide records are rejected as malformed.
- Company trends are ordered by reporting year/month rather than relying on unspecified database row order.
- Added regression tests for leap-year period boundaries and password-change behavior.

### Verification status
- Python bytecode compilation: passed.
- Pytest: blocked because `pwdlib` is absent; dependency installation was attempted but network/DNS access to the package index was unavailable.
- Ruff, PostgreSQL migration checks, Docker build, and manual acceptance: not run.

### Honest scope
These changes improve correctness and make verification expectations explicit. They do not establish that the application is production-ready, deployed, externally reviewed, secure against every threat, or used by real organisations.

## v3 — Evidence-first differentiation
- Added a specific product thesis focused on traceable portfolio reporting rather than generic CRUD breadth.
- Added adversarial reviewer challenges for tenancy, ingestion, auth, concurrency, financial correctness, and operability.
- Added authorship/provenance and claim-maturity rules to prevent inflated claims.
- Added release evidence and external review templates.
- Added a claim-to-artifact evidence ledger and PR discipline.
- Updated README and proof index to distinguish templates from completed verification.

