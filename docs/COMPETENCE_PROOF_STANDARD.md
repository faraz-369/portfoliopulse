# Competence Proof Standard

PortfolioPulse should let a skeptical reviewer verify how its author thinks, builds, tests, explains, and improves a backend system. A repository alone cannot prove a person's character or competence. Credibility emerges when the author independently explains the work, reproduces it, defends trade-offs, acknowledges limitations, and shows a traceable history.

## Five proof layers
| Layer | Reviewer can verify | Evidence |
|---|---|---|
| Authorship | What the author personally designed, implemented, tested, changed | Commit history, issue-to-change links, notes, live walkthrough |
| Technical competence | Understanding beyond memorised README | Code navigation, design defence, debugging exercise |
| Correctness | Stated behaviour is reproducible | Tests, fixtures, API responses |
| Engineering judgement | Risks and unresolved problems are understood | ADRs, threat model, failure analysis, limitations |
| Product judgement | System addresses a real workflow | Interview notes, observed workflow, feedback, prioritisation |

## Claim maturity labels
- **Implemented:** code exists.
- **Tested:** automated test exercises behaviour and result is recorded.
- **Verified locally:** documented manual procedure completed.
- **CI-verified:** CI passed on a named commit.
- **Externally reviewed:** named reviewer gave feedback, with permission for attribution.
- **Deployed:** reachable environment and deployment details exist.
- **Used:** real users used it; cohort and measurement are recorded.
- **Adopted:** a person/organisation made an evidenced decision to use it.

Never upgrade a claim without evidence.

## Non-negotiable integrity rules
1. Never fabricate commits, dates, users, customers, benchmarks, reviews, employment, or outcomes.
2. Do not backdate work. Label retrospective notes.
3. Distinguish implemented, tested, manually checked, externally reviewed, deployed, and adopted.
4. Use synthetic data unless explicitly authorised. Never publish confidential NIC/client data.
5. Do not call the project production-ready because it runs locally or has tests.
6. Attribute generated/assisted code honestly and understand what you present.
7. Preserve defects and corrections in the engineering log.
8. Invite reviewers to challenge the project and record what changed.

## Personal demonstration requirement
Without reading a prepared answer, the author should explain the user problem; draw request-to-database flow; trace CSV validation/persistence/error reporting; demonstrate tenant denial; explain one bug corrected; run tests and interpret a failure; defend three trade-offs and two rejected alternatives; and name current limitations and next risk. Record a single-take screen-and-voice walkthrough after practising.

This standard defines what proof to collect. It does not assert that the proof has already been collected.
