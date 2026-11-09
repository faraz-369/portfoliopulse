# PortfolioPulse Product Vision

## Status and evidence boundary

This is a product hypothesis for an independently built software demonstrator, not a validated commercial product. No customer interviews, adoption, operational savings, or customer outcomes are evidenced in this repository. The intended market and workflows below must be tested with real portfolio operations teams before they are treated as facts.

## Problem hypothesis

Accelerators, incubators, venture studios, and other portfolio operators may collect recurring performance information from multiple companies using spreadsheets and inconsistent reporting conventions. This may make it difficult for an operations analyst to validate submissions, identify missing or duplicate values, and produce a comparable portfolio view with traceable source data.

The hypothesis is deliberately narrow: recurring company metrics arrive as files, and a portfolio operations analyst needs a dependable way to validate and consolidate them. It does not assume that spreadsheets are currently causing measurable harm or that the proposed solution is preferable to existing tools.

## Target market hypothesis

- **Potential organisation:** a small or midsize accelerator, incubator, venture studio, or programme operator managing a portfolio of companies.
- **Potential workflow owner:** the person responsible for requesting and consolidating periodic operating metrics.
- **Potential contributors:** portfolio-company representatives who supply the data.
- **Potential stakeholders:** portfolio managers who interpret comparable trends.

These are research candidates, not confirmed buyers or users.

## Primary user and initial use case

**Primary target user:** a portfolio operations/reporting analyst who already receives company reports and is responsible for data quality and consolidation.

**Initial use case:** an analyst uploads a single-company, single-reporting-period CSV; the service validates it against a known schema and registered reporting period; accepted values are stored once; validation outcomes and submission history remain inspectable; authorised staff can retrieve company and portfolio summaries.

This matches the current service more closely than a self-service company portal. The present system has no company-representative account workflow, template configuration, or review/approval interface.

## Jobs to be done

1. Prepare a consistent reporting window and company roster.
2. Receive company metrics without silently coercing invalid values.
3. Identify which values failed and why.
4. Prevent accidental duplicate files and conflicting company-period metrics.
5. Reconcile summary figures to the persisted reporting record.
6. Restrict data to the correct organisation and role.

## Proposed value proposition

> PortfolioPulse is a backend-first reporting workflow demonstrator that helps a portfolio operations team validate recurring company metrics and inspect organisation-scoped summaries with a traceable submission record.

This is a proposed value proposition, not an outcome claim.

## Product boundaries

### Initial scope

- One organisation-scoped portfolio at a time for the signed-in user.
- Admin-managed company and reporting-period setup through the API.
- A fixed, versioned CSV contract for the first release.
- Analyst/admin submission of one company's metrics for one period per file.
- Explicit validation results, duplicate protection, submission history, and basic analytics.
- Read-only viewer access to authorised portfolio information.

### Explicitly out of scope until validated

- Multi-tenant customer onboarding, invitations, or company-representative accounts.
- Configurable templates, custom metric definitions, approval workflows, and bespoke dashboards.
- Integrations, billing, AI-generated recommendations, cloud hosting, an SLA, and regulatory certification.
- A claim that financial or operational metrics are audited, complete, or suitable for investment decisions.

## Assumptions requiring validation

1. Portfolio operators collect a recurring common subset of company metrics.
2. CSV ingestion is an important enough pain point to justify a dedicated workflow.
3. The portfolio operations analyst is willing and authorised to upload on companies' behalf.
4. A single-company, single-period file is acceptable for an initial workflow.
5. A fixed KPI definition is useful before configurable metric templates are needed.
6. Operators need per-row feedback and source traceability, not just a consolidated total.
7. Role boundaries of administrator, analyst, and read-only viewer fit real responsibilities.
8. The proposed deployment and data-retention model satisfies operators' confidentiality expectations.

### Validation plan

Conduct 5–8 structured, non-leading interviews with people who actually request, validate, and consolidate portfolio reporting. Ask about the last completed reporting cycle, file formats, reconciliation, exceptions, duplicate handling, approval responsibilities, access restrictions, and existing tools. Record anonymised notes only with permission. Do not present interview counts or findings until performed.

## Success measures for a demonstrator

These are acceptance measures, not achieved business outcomes:

- A new developer can start the documented local stack without modifying application code.
- The analyst can submit a valid file and see its stored result and source submission.
- Invalid values produce actionable feedback and do not silently become accepted values.
- A repeated upload or conflicting company-period is handled deterministically.
- Recomputed summary values can be reconciled to source metrics under documented KPI definitions.
- Tests establish permission boundaries and cross-organisation isolation.
- Every claimed capability is tied to executed tests or a reproducible demo.
