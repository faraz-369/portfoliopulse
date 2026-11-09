# Engineering decisions

- **Modular monolith:** one deployable backend keeps transaction boundaries and local development simple; modules separate API, persistence, processing and security.
- **FastAPI:** typed request validation and generated OpenAPI make the API inspectable.
- **PostgreSQL:** relational constraints and transactions fit tenant-scoped business reporting.
- **Decimal/Numeric:** financial arithmetic must not inherit binary floating-point rounding errors.
- **CSV ingestion:** explicit schema and row validation make data-quality failures visible.
- **Partial acceptance:** valid rows may persist while invalid rows are reported; all counts/statuses remain visible. A no-valid-row file is rejected.
- **Idempotency:** checksum rejects byte-identical re-uploads; unique metric constraint prevents a second accepted value for the same company/period.
- **Transactions:** metric, submission and logs are committed together; persistence exceptions roll back.
- **RBAC and tenant scope:** route dependencies check roles and tenant filters scope records.
- **API versioning:** `/api/v1` provides a stable namespace for future changes.
- **Synchronous processing:** appropriate for a bounded local demonstration; background workers can be added if file size/latency demands it.
- **Testing:** isolated DB fixtures protect demo data; extend integration tests before production use.
