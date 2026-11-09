# API reference

Interactive OpenAPI/Swagger: `/docs`. All business routes use `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Obtain JWT |
| GET | `/auth/me` | Current user |
| GET/POST | `/companies` | List/create companies |
| GET/PATCH/DELETE | `/companies/{id}` | Read/update/deactivate |
| POST | `/companies/{id}/submitters` | Create company-bound submitter (admin) |
| GET/POST | `/reporting-templates` | List/create organisation templates (admin creates) |
| POST | `/reporting-templates/{id}/versions` | Create immutable template version (admin) |
| GET/POST | `/reporting-periods` | List/create periods |
| POST | `/reports/upload` | Upload CSV |
| GET | `/reports` | List submissions |
| GET | `/reports/{id}` | Submission detail |
| GET | `/reports/{id}/errors` | Validation errors |
| GET | `/reports/{id}/logs` | Processing logs |
| GET | `/reports/{id}/events` | Submission state history |
| POST | `/reports/{id}/review` | Analyst/admin review |
| POST | `/reports/{id}/decision` | Admin approval/rejection after review |
| GET | `/organizations/me` | Current user's organisation |
| POST | `/auth/change-password` | Change current user's password |
| GET | `/analytics/portfolio/overview` | Portfolio KPIs |
| GET | `/analytics/companies/{id}/overview` | Company totals |
| GET | `/analytics/companies/{id}/trends` | Company time-series |
| GET | `/audit-logs` | Admin audit records |
| GET | `/processing-logs` | Admin/analyst processing records |

Uploads use the reporting period's immutable template version. A failed validation is retained as `validation_failed` and returns HTTP 422 with `submission_id`, counts and structured errors. Corrected uploads reference the failed submission and create new history. Valid uploads are `pending_review`; an admin can decide only after an analyst or admin has recorded a review. Only approved reports contribute to analytics. Rejected, validation-failed, pending-review and superseded submissions are excluded.

Portfolio overview values are calculated from each company's latest approved report; missing values remain `null`. The response declares `reporting_basis`, `periods_may_differ`, and period coverage because companies may report for different months.
