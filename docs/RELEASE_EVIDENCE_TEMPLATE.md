# Release Evidence Record

Copy for every release candidate. Never mark a check complete unless it was run and its output retained.

## Identity
- Release/tag:
- Commit SHA:
- Date/timezone:
- OS / Python / database versions:

## Reproduction
- [ ] Fresh checkout
- [ ] Dependencies installed from pinned requirements
- [ ] Environment configured from `.env.example`
- [ ] Database created from migrations
- [ ] Demo seed completed
- [ ] API starts
- [ ] Frontend starts

## Automated verification
| Command | Result | Evidence location |
|---|---|---|
| `ruff check .` | NOT RUN | |
| `pytest -q` | NOT RUN | |
| `pytest --cov=app --cov-report=term-missing` | NOT RUN | |
| `alembic upgrade head` against PostgreSQL | NOT RUN | |
| Docker Compose build | NOT RUN | |
| Docker Compose smoke test | NOT RUN | |

## Manual verification
| Scenario | Expected result | Observed result | Evidence |
|---|---|---|---|
| Admin login | Token returned | NOT RUN | |
| Analyst admin-only action | Denied | NOT RUN | |
| Valid CSV | Valid rows persisted | NOT RUN | |
| Invalid CSV | Row-level errors explained | NOT RUN | |
| Duplicate file | Rejected | NOT RUN | |
| Cross-tenant access | Denied; no data leak | NOT RUN | |
| Analytics | Matches source records | NOT RUN | |

## Defects and limitations
- Known defects:
- Accepted risks:
- Deferred work:
- Data used (synthetic/real with permission):
- External reviewer and scope:

## Release decision
- [ ] Not releasable
- [ ] Local demo only
- [ ] Public portfolio demo
- [ ] Limited pilot (requires explicit safeguards and operational review)

A passing test suite does not automatically justify a production-ready label. State exactly what this release is safe to demonstrate.
