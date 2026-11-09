# Database design

Entities include Organization, User, Company, ReportingTemplate, TemplateMetric, ReportingPeriod, ReportSubmission, SubmissionEvent, CompanyMetric, ProcessingLog and AuditLog. Tenant-owned tables carry `organization_id`; PostgreSQL composite foreign keys bind users, companies, periods, templates, submissions, metrics, and events to the same organisation. A period references a specific immutable template version. Company metrics are staged per submission; an approved-submission partial unique index enforces one current approved report per company/period. Metric columns allow `NULL` for optional template metrics, with non-negative checks where values are present.

```mermaid
erDiagram
 ORGANIZATION ||--o{ USER : contains
 ORGANIZATION ||--o{ COMPANY : owns
 ORGANIZATION ||--o{ REPORTING_PERIOD : defines
 ORGANIZATION ||--o{ REPORTING_TEMPLATE : configures
 REPORTING_TEMPLATE ||--o{ TEMPLATE_METRIC : defines
 REPORTING_TEMPLATE ||--o{ REPORTING_PERIOD : selected_for
 COMPANY ||--o{ REPORT_SUBMISSION : receives
 REPORTING_PERIOD ||--o{ REPORT_SUBMISSION : scopes
 REPORT_SUBMISSION ||--o{ COMPANY_METRIC : creates
 REPORT_SUBMISSION ||--o{ SUBMISSION_EVENT : records
 REPORT_SUBMISSION ||--o{ PROCESSING_LOG : records
 ORGANIZATION ||--o{ AUDIT_LOG : records
```

UUID strings are used as portable identifiers. Monetary values use `NUMERIC(18,2)`. Timestamps are UTC-aware at the application boundary. Alembic owns schema lifecycle.
