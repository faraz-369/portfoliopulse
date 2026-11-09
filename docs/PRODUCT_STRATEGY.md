# PortfolioPulse — Product Strategy & Problem Definition

## Product in one sentence
PortfolioPulse is a multi-tenant reporting backend that helps a portfolio or programme operations team collect monthly company metrics, validate submissions, preserve an audit trail, and inspect comparable portfolio-level performance.

## The problem hypothesis
Teams that monitor multiple companies often receive recurring spreadsheets in inconsistent formats. A spreadsheet-based process can make it difficult to:
- know which companies have submitted a period's report;
- detect malformed, duplicated, or inconsistent rows;
- preserve a traceable record of who submitted what;
- compare companies and periods using consistent calculations;
- restrict access to the right organisation and role.

This is a **problem hypothesis**, not a claim that a named customer has validated it. PortfolioPulse is a portfolio engineering demonstrator built around that workflow.

## Intended users
| User | Job to be done | Relevant capability |
|---|---|---|
| Portfolio administrator | Configure companies, reporting periods and access | Admin-scoped management |
| Analyst / programme associate | Upload monthly data and resolve validation issues | CSV ingestion, validation feedback, logs |
| Read-only stakeholder | Inspect company and portfolio summaries | Read-only analytics access |

These are target personas, not confirmed users or customers.

## Core workflow
1. An administrator creates an organisation, companies and reporting periods.
2. An analyst submits a CSV for a reporting period.
3. The backend validates the file and each row against schema and business rules.
4. Valid records are persisted; invalid records are reported with row-level explanations.
5. The submission and processing events remain inspectable.
6. Authorised users query company and portfolio summaries.
7. Duplicate submissions and cross-organisation access are rejected.

## Why a backend-first product?
The engineering problem is primarily data integrity, access control, repeatable business rules and traceability. The Streamlit client is intentionally a thin demonstration interface. The core product value is in the API, domain logic, persistence model and verifiable behaviour.

## Product boundaries
Included: organisation-scoped data, user roles, companies, periods, CSV ingestion, validation, duplicate protection, KPI summaries, logs, API and a thin demo client.

Not included: production customer onboarding, billing, external integrations, asynchronous job orchestration, enterprise SSO, advanced BI, regulatory certification, formal SLA or a professional security audit.

## Success criteria for a portfolio demonstrator
These are acceptance criteria to verify, not achieved outcomes:
- A reviewer can start the stack from documented instructions.
- A reviewer can authenticate and observe role restrictions.
- A valid CSV creates the expected records.
- An invalid CSV returns precise row/column errors without silently changing values.
- Repeating a submission is handled deterministically.
- Analytics are reproducible from known input data.
- Organisation boundaries are enforced and tested.
- A reviewer can trace a design decision to code and tests.

## Product validation plan
Before calling this a validated product, conduct 5–8 structured problem interviews with people who actually handle recurring portfolio/programme reporting. Ask about their current workflow, frequency, failure modes, reconciliation effort, access requirements and existing tools. Do not pitch first. Record anonymised notes only with permission. A problem is validated only when multiple independent interviewees describe materially similar pain and a current workaround.

## Positioning statement
“PortfolioPulse is an independently built backend engineering demonstrator for organisation-scoped portfolio reporting. It showcases API design, relational data modelling, CSV validation, deterministic KPI logic, access control and testable data workflows.”

Avoid “production-grade”, “enterprise-ready”, “used by investors”, “saved teams hours” or “customer-validated” unless separate evidence is obtained.
