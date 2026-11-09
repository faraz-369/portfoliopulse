# PortfolioPulse proof index

Use this index to help a reviewer independently inspect claims. The repository is a self-directed portfolio project using synthetic data.

| Claim | Evidence location | Current evidence status |
|---|---|---|
| Backend API implementation | `backend/app/main.py`, `backend/app/schemas.py` | Source present; runtime verification pending |
| Relational persistence model | `backend/app/models.py`, `backend/alembic/` | Source present; PostgreSQL migration verification pending |
| CSV ingestion and validation | `backend/app/processing.py`, `backend/tests/test_processing.py` | Source and tests present; full suite blocked |
| Authentication and role checks | `backend/app/security.py`, `backend/tests/test_api.py` | Source and regression tests present; full suite blocked |
| Tenant-scoped query patterns | `backend/app/main.py` | Source inspection required; adversarial cross-tenant test coverage still needs expansion |
| Reproducible local deployment | `docker-compose.yml`, `docs/deployment.md` | Configuration present; Docker build/run not verified |
| Engineering reasoning | `docs/architecture.md`, `docs/engineering_decisions.md`, `docs/ENGINEERING_DEFENSE.md` | Documentation present; must be defended by the author |
| Release verification | `docs/RELEASE_VERIFICATION.md` | Protocol present; checks not yet completed |
| Eight months of historical work experience | Separate employer/NIC records | Not established by this repository |
| Real users, production use, revenue, customer impact | External deployment/customer records | Not established |

## Evidence capture rules

1. Capture the commit SHA before running checks.
2. Preserve raw command output and exit codes.
3. Keep test failures and limitations; do not curate them away.
4. For a demo, record the exact commit and use only synthetic data unless authorised real data is explicitly available.
5. Ask an independent reviewer to reproduce setup and challenge the architecture.
6. Attribute all work accurately. Do not imply this project was built for NIC or a former employer.

## Reviewer-grade evidence framework
- `docs/COMPETENCE_PROOF_STANDARD.md` — claim maturity and personal demonstration standard.
- `docs/REVIEWER_CHALLENGE_PACK.md` — adversarial review scenarios.
- `docs/AUTHORSHIP_AND_PROVENANCE.md` — authorship and work-history provenance.
- `docs/PRODUCT_DIFFERENTIATION.md` — product thesis and proof requirements.
- `docs/EXTERNAL_REVIEW_REQUEST.md` — independent technical review request.
- `docs/RELEASE_EVIDENCE_TEMPLATE.md` — repeatable release verification record.
- `docs/EVIDENCE_LEDGER_TEMPLATE.csv` — claim-to-artifact evidence ledger.
- `.github/pull_request_template.md` — issue/change/verification discipline.

These are protocols and templates, not proof that checks have passed.

