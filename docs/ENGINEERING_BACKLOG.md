# Prioritised Engineering Backlog

Prioritise proof of correctness before adding breadth.

## P0 — release blockers / verify first
- [ ] Install dependencies in a clean Python 3.12 environment.
- [ ] Run Ruff and fix all findings.
- [ ] Run the complete pytest suite and record exact output.
- [ ] Run Alembic migration against an empty PostgreSQL database.
- [ ] Run clean Docker Compose startup and exercise documented demo workflow.
- [ ] Add cross-organisation access tests for every resource family.
- [ ] Add role matrix tests for admin, analyst and viewer.
- [ ] Add transaction rollback test for unexpected failure during ingestion.
- [ ] Verify duplicate detection for identical file and same company-period with different file bytes.
- [ ] Reconcile KPI output against hand-calculated fixtures.
- [ ] Ensure README instructions match actual commands and routes.

## P1 — engineering depth
- [ ] Separate route handlers from service and repository layers.
- [ ] Add explicit pagination metadata and stable ordering to list endpoints.
- [ ] Define API error response conventions.
- [ ] Add request IDs and structured application logging.
- [ ] Add file content validation, encoding handling and robust malformed CSV tests.
- [ ] Add migration upgrade test in CI using PostgreSQL.
- [ ] Add dependency vulnerability scanning and pin/review dependencies.
- [ ] Add backup/restore runbook for a real deployment target.
- [ ] Add performance baseline with defined dataset and hardware; do not use “scalable” without this.

## P2 — product validation and usability
- [ ] Conduct 5–8 discovery interviews with portfolio/programme reporting operators.
- [ ] Write anonymised problem findings and distinguish observed facts from assumptions.
- [ ] Test whether CSV upload and validation match real workflows.
- [ ] Add an exportable validation report if users need it.
- [ ] Add reporting completeness view if users identify it as a priority.
- [ ] Improve demo UI only where it helps a reviewer understand the backend workflow.

## Definition of done
A backlog item is done only when implementation, tests, documentation and verification evidence are linked. “Code written” is not the same as “feature verified”.
