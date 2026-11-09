# Product and Engineering Roadmap

## Prioritisation

Priority weighs business value, engineering value, risk reduction, and effort. **P0** is a blocker for a credible MVP; **P1** is required for a coherent first release; **P2** follows after core behavior is reliable; **P3** is conditional on user evidence. Effort is relative: S / M / L.

## Phase 0 — Product and engineering foundation

**Objective:** make current claims honest, choose the initial workflow, and remove correctness/quality blockers without expanding scope.

| Priority / effort | Work |
|---|---|
| P0 / S | Confirm analyst-on-behalf-of-company workflow, one-file/one-company-period limit, KPI meaning, currency, and stock-vs-flow semantics with product owner. Keep hypotheses explicitly unvalidated. |
| P0 / S | Fix reporting-period response schema/test contract and seeded period end dates. |
| P0 / M | Define portfolio and company KPI semantics; correct customer/employee snapshot aggregation and deterministic latest-period selection. |
| P0 / M | Make all-invalid CSV feedback actionable and preserve a safe submission/error record or return structured errors consistently; choose one API contract. |
| P0 / M | Make backend Ruff and pytest CI gates green; retain useful linting rather than weakening checks. |
| P1 / M | Add unit tests for every CSV rule, date boundaries, KPI aggregation and duplicate behavior. |
| P1 / M | Add authorization matrix and cross-tenant tests for companies, periods, submissions, logs, analytics and mutations. |
| P1 / S | Review current model/route contracts and document one-company/one-period CSV boundary. |

**Dependencies:** product owner decisions on period granularity, KPI definitions, and no-valid-row behavior.

**Acceptance criteria:** period response exposes documented bounds; leap/common-year boundaries are correct in API and seed; KPIs reconcile against known fixtures; malformed/all-invalid/partial-valid files return documented feedback; existing business data is not overwritten; Ruff and full pytest pass.

**Tests:** focused unit tests, isolated API tests, cross-tenant tests, transaction rollback tests.

**Demonstration evidence:** clean test output, API request/response examples, and a small reconciled fixture.

**Definition of done:** baseline claims match code and behavior; no known P0 correctness defect remains.

**Implementation follow-up:** the reporting-period bounds, KPI semantics, deterministic latest-per-company portfolio aggregation, persisted all-invalid upload errors, focused regression tests, and Ruff cleanup are implemented. The current backend test suite passes (21 tests), Ruff passes, and Compose/API/UI checks were exercised locally. Broader cross-tenant authorization tests remain incomplete, so Phase 0's complete acceptance criteria are not all met.

## Phase 1 — Coherent MVP

**Objective:** deliver one end-to-end staff-operated reporting workflow with reliable validation and insight.

| Priority / effort | Work |
|---|---|
| P1 / M | Admin can configure portfolio companies and reporting periods through stable API and minimal UI or documented Swagger workflow. |
| P1 / M | Analyst uploads one company's one period of metrics and can inspect submission status and row-level outcomes. |
| P1 / M | Add clear submission list/detail, validation error retrieval, and links from analytics to the source report. |
| P1 / M | Define fixed KPI catalog, data types, units/currency, requiredness, and period semantics. |
| P1 / M | Viewer sees company-period metrics and accurately defined portfolio aggregates, not summed snapshots. |
| P1 / S | Make the synthetic demo script executable against a fresh local stack and safe to rerun without deleting persistent data. |

**Dependencies:** Phase 0; explicit initial workflow; agreed reporting and KPI contract.

**Acceptance criteria:** seeded/admin setup; an analyst can submit valid and partially invalid CSV; accepted record is traceable; errors are actionable; duplicate attempts are deterministic; viewer analytics reconcile to fixtures; tenant/role tests pass.

**Tests:** full API integration path on PostgreSQL; error and duplicate cases; permission matrix; manual Streamlit and Swagger walkthrough.

**Demonstration evidence:** dated test/Compose logs, request/response examples, source-to-KPI reconciliation, and screenshots without credentials or tokens.

**Definition of done:** a reviewer can complete the narrow workflow without editing code or interpreting undocumented behavior.

## Phase 2 — Engineering depth

**Objective:** protect data integrity, traceability, and behavior under realistic failure.

| Priority / effort | Work |
|---|---|
| P1 / M | Add database constraints/indexes for tenant-consistent references where supported and document integrity boundaries. |
| P1 / M | Make duplicate writes concurrency-safe and translate constraint failures into stable 409/idempotent responses. |
| P1 / M | Add report revision/supersession or correction semantics only after owner chooses whether prior metrics remain immutable. |
| P1 / M | Expand audit trail to security-sensitive administration and configuration changes, with retention/access policy. |
| P2 / M | Add versioned KPI definitions and reproducible aggregation tests. |
| P2 / S | Add bounded report/log pagination and query performance tests against representative data. |
| P2 / M | Add PostgreSQL integration and migration regression tests, including transaction rollback and restart. |

**Dependencies:** stable MVP contracts and product decisions on revisions, audit retention, and tenant membership.

**Acceptance criteria:** no duplicate metric under concurrent requests; every metric can be traced to source/version; all tenant boundaries and mutation permissions have automated tests; query sizes remain bounded.

**Tests:** PostgreSQL integration, concurrency, migration upgrade, rollback, and property/boundary tests.

**Demonstration evidence:** repeatable concurrency and migration outputs; traceability examples.

**Definition of done:** critical data invariants are enforced by both application behavior and database constraints where feasible.

## Phase 3 — Operational maturity

**Objective:** operate the application predictably beyond one developer machine.

| Priority / effort | Work |
|---|---|
| P1 / M | Remove unsafe deployment defaults; validate required secrets/settings at startup; document secret rotation. |
| P1 / M | Add backend/frontend healthchecks, migration orchestration policy, service readiness dependencies, and safe shutdown behavior. |
| P1 / M | Add automated backup and a tested restore procedure, retention, and data-loss recovery objectives. |
| P1 / M | Add structured, redacted logs, request correlation, useful metrics, and actionable health/readiness details. |
| P2 / M | Establish dependency/image update and vulnerability scanning process. |
| P2 / M | Add deployment target only after user, data residency, access, cost, and operational needs are established. |
| P2 / S | Add reproducible install/test instructions and record clean CI evidence. |

**Dependencies:** security and operational owners, retention needs, deployment target decision.

**Acceptance criteria:** no default development secret can boot a shared deployment; healthchecks distinguish readiness; restore passes a documented drill; logs contain no credentials/tokens; CI and migration checks are green.

**Tests:** settings validation, compose integration, restore drill, log redaction tests, security scanning.

**Demonstration evidence:** dated restore report, CI link, healthcheck status, redacted logs.

**Definition of done:** an operator other than the author can deploy, observe, recover, and maintain the service using documented procedures.

## Phase 4 — Product differentiation (conditional)

**Objective:** add only capabilities linked to validated user needs.

| Candidate | User problem / value | Complexity | Priority |
|---|---|---:|---|
| Versioned reporting templates and rules | Teams may need different fields, units, and periods; avoids hardcoded schema deployments. | L | P3, after repeated evidence of variation |
| Submission schedule and completeness tracking | Analyst may need to know who has not reported. | M | P2/P3, after discovery confirms this need |
| Formal review/approval and resubmission history | Portfolio team may require accountable sign-off and immutable revisions. | M/L | P3, only if workflow interviews show required controls |
| Export/reconciliation reports | Analysts may need to reuse results in board or programme reporting. | M | P2/P3, after validating output formats |
| Background processing | Useful only if real file sizes/latency exceed safe synchronous limits. | M/L | Defer until measured |
| Advanced dashboards/AI | No current evidence establishes a need or trustworthy basis. | M/L | Do not schedule absent validated use case |

**Acceptance criteria:** each feature has an identified user, observed problem, measurable acceptance test, and traceability back to the source data. Technology selection follows workload evidence, not fashion.

## Recommended next development sprint

Do not begin feature expansion. The next sprint should be a **Phase 0 correctness sprint**:

1. Agree and document KPI semantics (revenue/expenses as flows; customer and employee counts as snapshots).
2. Fix reporting-period response and seeded bounds.
3. Fix analytics ordering/aggregation to match those semantics.
4. Define and implement one all-invalid-file error contract with a safe persisted or response-only result.
5. Add focused ingestion, KPI, and date tests; restore green Ruff and complete pytest gates.
6. Run the existing Compose E2E scenario and capture reproducible evidence.

**Sprint acceptance:** a clean full backend suite and lint pass; API/seed date parity; fixture-reconciled analytics; stable invalid-file feedback; no changes to demo passwords or unrelated application behavior.

## MVP completion criteria

The MVP is complete only when all of the following are true:

1. A developer can follow README instructions to start the application and reach healthy API, database, and UI services.
2. The system can represent one organisation, its companies, and valid reporting periods with stable identifiers and enforceable tenant boundaries.
3. An authorised analyst can submit a CSV for one company and one reporting period using a documented contract.
4. Valid, partial-valid, all-invalid, malformed, oversized, repeated-file, and already-reported-period cases have stable documented outcomes.
5. Accepted metrics, submission status, validation outcomes, and processing/audit history persist consistently and can be retrieved.
6. Company and portfolio KPIs have explicit definitions, correctly handle time-series stocks/flows, and reconcile to test fixtures.
7. Role and cross-organisation tests cover every resource and mutation; viewer cannot write or upload.
8. Database migrations work from an empty database and upgrade a representative prior schema without deleting application data.
9. The full automated suite and lint gates pass in CI; tests do not depend on production data.
10. A dated demo can be repeated from a disposable local environment and captured without exposing secrets or claiming customer validation.
