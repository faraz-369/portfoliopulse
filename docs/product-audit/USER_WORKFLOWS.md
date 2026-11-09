# Users and Reporting Workflows

## Stakeholders

| Stakeholder | Responsibilities and objectives | Information needed | Current interaction and permission | Proposed value / gap |
|---|---|---|---|---|
| Portfolio manager | Monitor company progress and identify portfolio-level patterns. | Comparable, period-aware metrics; submission coverage; exceptions and source lineage. | Current `viewer` can read portfolio/company data and reports. | Consolidated view is a plausible value proposition; current aggregate definitions and coverage indicators are insufficient. |
| Portfolio-company representative | Provide accurate information on time and correct rejected values. | Reporting requirements, deadline, accepted schema, validation feedback, submission status. | No dedicated role, account provisioning, portal, or direct submission flow. | Future user only; initially the analyst may upload on the company's behalf. |
| Reporting analyst / programme associate | Request, collect, validate, reconcile, and follow up on reporting. | Company/period status, row-level errors, duplicates, history, and reproducible totals. | `analyst` can upload and read processing logs; cannot create companies or periods. UI has CSV upload and import history. | Best initial user: this maps to the currently implemented backend workflow. |
| Organisation administrator | Configure the organisation, users, portfolio roster, periods, and access. | Membership, role assignments, active state, configuration and audit trail. | `admin` can create/update/deactivate companies, create periods, inspect audit logs; no API for org or user provisioning. | Can administer a seeded tenant but cannot onboard a real tenant or manage its users end to end. |

The personas are hypotheses. No actual user research is represented here. The table below records a pre-reporting-lifecycle baseline; the current implementation is described in the sprint status section below and verified in [`RELEASE_VERIFICATION.md`](../RELEASE_VERIFICATION.md).

## Reporting lifecycle sprint status

The current demonstrable workflow is: an admin configures an organisation-owned immutable template version and period; a staff analyst or company-bound submitter uploads one-company/one-period CSV; validation errors are retained and corrections create linked submissions; an analyst/admin records review; an admin approves or rejects after review; only approved records feed analytics; state events and audit records preserve traceability. The Streamlit UI exposes template/period setup, company and company-submitter creation, upload/correction, review/decision, portfolio analytics, processing history, and admin audit history.

PostgreSQL composite foreign keys enforce tenant consistency across linked records. A dedicated PostgreSQL integration test target covers these constraints and ingestion transaction behavior. No report requests/deadlines, background processing, arbitrary user-defined metric types, hosted deployment, production adoption, or formal security certification is claimed.

## Recommended smallest coherent workflow

Keep the first product narrow: one organisation; admin configures a company and period; analyst uploads a CSV with one company's metrics for that period; service validates and persists accepted data with an inspectable submission; analyst can retrieve results/errors; viewer can inspect period-aware company and portfolio summaries. Do not require company self-service, configurable templates, formal approvals, or background processing for this initial scope.

## End-to-end workflow map

“Current” describes code behaviour, not completeness. The table records the actor, input, backend/database work, output/failure, and permission boundary at each stage.

| Step | Actor and input | Backend operation / database change | Output and important failures | Permission / current support |
|---|---|---|---|---|
| 1. Organisation setup | Administrator supplies organisation identity and first administrator. | Intended system creates `Organization` and membership. Current setup is only in the seed script; no provisioning endpoint. | No production onboarding or tenant creation API. | Current demo only. |
| 2. Company registration | Admin supplies identifier, name, industry, optional description/website. | `POST /api/v1/companies` writes a tenant-owned `Company` and an audit row. | Duplicate identifier check returns 409; a race/slug collision may surface as an unhandled database error. | Admin-only API; no setup UI. |
| 3. Period creation | Admin supplies year and month. | `POST /api/v1/reporting-periods` calculates calendar bounds and persists a `ReportingPeriod`. | Duplicate period returns 409; year/month validation returns 422. `PeriodOut` exposes actual month bounds. | Admin-only API; no setup UI. |
| 4. Reporting requirements | Admin defines metrics, schema, deadline, and rules. | A complete product would persist a versioned template and apply it to a period. Current schema is a fixed `REQUIRED` list in code. | Template changes are code deployments; no per-organisation rules. | Missing as a configurable workflow. |
| 5. Report request | Analyst requests data from the company and records due date/status. | A complete product would create period-specific assignments/reminders. No request/assignment entity or route exists. | No missing-submission tracking or reminders. | Missing. |
| 6. Company submission | Company representative uploads a file or enters structured values. | Intended system authenticates a company user and records submitter/source. Current `POST /api/v1/reports/upload` accepts admin/analyst uploads only. | No company identity or direct submitter workflow. | Partially supported as staff upload. |
| 7. File receipt | Analyst/admin sends a `.csv` multipart file. | Route reads up to configured limit plus one byte; `ingest` checks size, extension and SHA-256 against tenant submissions. | Over-limit, non-CSV, or byte-identical file becomes HTTP 400. File is processed synchronously in memory. | Admin/analyst only. |
| 8. Structural validation | Service receives UTF-8/UTF-8-BOM CSV with exact nine-column header. | `parse_and_validate` checks encoding/header, blank/malformed rows, numeric formats and duplicates. | A file with no accepted rows is persisted as a failed submission; the HTTP 422 response and report error endpoint expose structured row/file errors. | Implemented; tests cover invalid-only and partial uploads. |
| 9. Business validation | Service resolves a company, reporting period, nonnegative metrics, and customer-count relationships. | Tenant-scoped queries resolve `Company` and `ReportingPeriod`; `Decimal` and integer checks validate values. | Unknown company, invalid period, negative/non-finite amounts, invalid counts, and new customers above total are rejected. Some validation errors are per-row; unexpected exceptions are broadly converted to validation messages. | Fixed rules, no template versioning. |
| 10. Duplicate handling | Service compares row key, file checksum, and company-period metric. | SHA-256 duplicate file check; database unique constraints protect submission checksum and company-period metric. | Identical file gets 400; already-reported metric is reported as a duplicate if other valid data allows a submission. Check-then-insert can race; no explicit retry/idempotency key. | Partially implemented. |
| 11. Processing and persistence | Service has at least one valid row, one company, one period. | Writes `ReportSubmission`, `CompanyMetric`, and `ProcessingLog` rows in one SQLAlchemy transaction, then commits. | Persistence exception rolls back. Mixed accepted/rejected rows are represented; files with valid rows from multiple companies or periods are rejected. | One-company/one-period file, synchronously processed. |
| 12. Error correction | Analyst reviews row issues and submits corrected data. | Current errors are returned from upload response or read from validation log via `/reports/{id}/errors`. | No correction link, draft, or submission version exists. The UI displays persisted failure details. | Partial API support. |
| 13. Review/approval | Analyst reviews, approves, or rejects company submission. | A complete workflow needs explicit state transitions and reviewer identity/timestamps. Current status moves directly to completed/completed-with-errors. | No approval or rejection records, reopen, or supersession. | Missing. |
| 14. Aggregation | Viewer/analyst queries a company or portfolio view. | Analytics routes query tenant-scoped metrics and calculate totals. | Company overview sums flow metrics and selects latest snapshot metrics; portfolio overview selects each company's latest report and exposes reporting-period coverage. Those periods may differ. | Implemented; semantics are documented and fixture-tested. |
| 15. Dashboard/reporting | Viewer sees metrics and drills into source records. | Streamlit calls overview, company list, upload, and report list routes. | No period selector, coverage indicator, exports, or dashboard lineage links. Company/company analytics are available through API only. | Thin demo UI. |
| 16. Audit and operations | Admin/analyst investigates actions and processing outcomes. | `AuditLog` and `ProcessingLog` queries are tenant-scoped; selected actions write audit events. | Not all admin mutations are logged; retention/export/backup policies are absent. | Partial. |

## Permission matrix (current)

| Operation | Admin | Analyst | Viewer |
|---|---:|---:|---:|
| Login and `/auth/me` | Yes | Yes | Yes |
| Read tenant companies, periods, reports, analytics | Yes | Yes | Yes |
| Create/update/deactivate company | Yes | No | No |
| Create reporting period | Yes | No | No |
| Upload CSV | Yes | Yes | No |
| Read processing logs | Yes | Yes | No |
| Read audit logs | Yes | No | No |
| Manage organisation/users or company identities | No route | No route | No route |

The matrix is inferred from route dependencies in `backend/app/main.py`; it has not been exhaustively verified with one test per role/resource.

## Failure scenarios to make explicit

- The organisation or company does not exist, is inactive, or is outside the current tenant.
- The period is not registered, incorrectly bounded, closed, or has not been requested.
- CSV encoding, header, row width, decimal precision, or count constraints are invalid.
- All rows are invalid; the current API returns a generic 400 without a persisted submission or retrievable row errors.
- The file repeats or another request inserts the same company-period metric concurrently.
- The database fails during processing; all writes should roll back and the client should receive a stable, non-sensitive error.
- The backend is unavailable while Streamlit attempts login or data retrieval.
- A report has valid data but not all required companies have submitted; current analytics do not distinguish missing from zero.
- A value is corrected later; current system has no version/supersession rule.
