# Testing strategy

Run `cd backend; pytest -q` or `pytest --cov=app --cov-report=term-missing`. The fast API/workflow tests use isolated in-memory SQLite through dependency overrides, never the demo database. They cover authentication, template version history, validation and correction, review/decision transitions, approved-only analytics, audit history, tenant-scoped API access and seed idempotence.

PostgreSQL-specific constraint tests use a dedicated database whose name ends in `_test`. Set `PORTFOLIOPULSE_TEST_DATABASE_URL` and run `pytest -q tests/test_postgres_integration.py`. The fixture drops and recreates tables in that database, so do not point it at the application/demo database. The tests exercise composite tenant foreign keys, template/period consistency, submission/metric consistency, approved-report uniqueness and transaction rollback.
