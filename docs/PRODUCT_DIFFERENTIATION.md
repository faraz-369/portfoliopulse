# Product Differentiation

## The weak version to avoid
A generic CRUD dashboard with login, charts, CSV upload and a README is common. Those features alone do not demonstrate strong backend engineering.

## Product thesis
PortfolioPulse explores a specific operational workflow: an organisation collects periodic operating and financial reports from portfolio companies, validates submissions, preserves an audit trail, and produces comparable portfolio-level views without silently accepting bad data.

This raises meaningful backend questions: reporting-period correctness; tenant isolation; row-level validation; duplicate-file and duplicate-period handling; financial precision; traceability from dashboard numbers to source submissions; mixed-validity batch semantics; and operator investigation of failed submissions.

## Differentiation must be demonstrated
| Differentiator | Evidence required | Current status |
|---|---|---|
| Explainable ingestion | fixtures, row-level error cases, API responses, tests | Implemented in code; full suite not verified |
| Tenant-aware access | cross-tenant tests for every resource and mutation | Partial; adversarial coverage required |
| Financial correctness | Decimal tests, rounding policy, boundaries | Decimal used; broader verification required |
| Traceability | submission IDs, logs, audit records, source lineage | Some records implemented; end-to-end review required |
| Operational maturity | migrations, backup/restore, readiness, logs | Not established |
| Product validation | observed workflow and user feedback | Not established |
| Independent credibility | external review and reproducible setup | Not established |

## Signature demonstration
1. Admin creates a company and reporting period.
2. Analyst uploads a deliberately mixed-quality CSV.
3. API accepts valid data and reports specific validation failures.
4. Exact duplicate upload is prevented.
5. Portfolio view updates from persisted records.
6. Authorised user traces the result to its submission and processing log.
7. A different organisation cannot access those records.

This story is the product's core proof. It must be covered by automated tests and a reproducible demo before being advertised as verified. Avoid feature bloat, unnecessary AI, microservices, or elaborate dashboards added only to look advanced.
