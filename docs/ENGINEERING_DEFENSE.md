# Engineering Defence — Questions You Must Be Able to Answer

These are not scripts to memorise. Use them to test whether you understand the system. Adapt each answer to the actual implementation and say “not implemented” where appropriate.

## 1. What problem does PortfolioPulse solve?
**Answer:** It addresses a common reporting workflow: collecting periodic metrics from multiple companies, validating submissions, preserving processing history and producing comparable summaries. It is an independently built demonstrator, not a deployed customer product. The problem hypothesis still needs interviews with target users.

## 2. Why did you choose a modular monolith?
**Answer:** The domain is cohesive and the current workload does not justify distributed services. A modular monolith keeps deployment and local development simpler while allowing separation between HTTP/API concerns, domain services, processing and persistence. Microservices would add network, deployment and consistency costs without demonstrated need.

## 3. Why PostgreSQL and a relational model?
**Answer:** The domain has clear relationships and integrity requirements: users belong to organisations, companies belong to organisations, submissions refer to companies and periods, and metrics must reference valid submissions. Foreign keys, unique constraints and transactions make these invariants enforceable at the persistence layer.

## 4. Why organisation scoping?
**Answer:** The system models multiple organisations. Every authenticated request must be constrained by the caller's organisation, not merely by possession of a resource identifier. The proof is negative integration tests showing a user from one organisation cannot retrieve or mutate another organisation's records. If those tests are absent or fail, tenant isolation is not proven.

## 5. Why use Decimal for financial values?
**Answer:** Binary floating-point cannot represent many decimal fractions exactly. Financial calculations need predictable decimal arithmetic and explicit rounding rules. The implementation should keep money as Decimal from parsing through persistence and response serialization.

## 6. How does CSV validation work?
**Answer:** There are file-level checks (format, required headers, size) and row-level checks (types, required values, business constraints, company and period references). Errors should identify the row, column and reason. Invalid data should never be silently coerced into a different business value.

## 7. What does partial acceptance mean?
**Answer:** Valid rows can be accepted while invalid rows are reported, provided the product policy explicitly allows it. The submission status and counts must make partial success visible. Unexpected infrastructure or persistence failures are different: they should roll back the transaction rather than leave an ambiguous partial state.

## 8. How do you prevent duplicate uploads?
**Answer:** A file checksum can detect byte-identical uploads. A database uniqueness constraint on the business key (for example company plus reporting period) protects against semantically duplicate metrics even if file formatting differs. These are different protections and both need tests. A replacement workflow must be explicit and transactional.

## 9. What is the difference between health and readiness?
**Answer:** Liveness indicates the process is running. Readiness indicates dependencies required to serve traffic—such as the database—are reachable. A process can be alive but not ready.

## 10. What do your tests prove?
**Answer:** Only the behaviour exercised by the tests, under the tested configuration. Unit tests prove isolated logic; integration tests exercise API/database interactions; negative tests are important for permissions and tenant boundaries. A test file existing is not proof that tests pass. I report the exact command and result.

## 11. Is this production-ready?
**Answer:** No such claim is justified. It is a portfolio demonstrator. Production readiness would require further work such as threat modelling and security review, operational monitoring, backup/restore drills, load testing, deployment automation, secrets management, incident procedures and user validation.

## 12. Why Streamlit?
**Answer:** It provides a lightweight way to demonstrate API workflows without diverting the project into frontend engineering. The client calls the backend over HTTP; it does not bypass the API or connect directly to the database.

## 13. What would you improve next?
**Answer:** First close correctness and verification gaps: tenant-isolation tests, transaction rollback tests, migration verification, deterministic KPI tests and a successful clean Docker run. Then improve API pagination/filtering, observability, background processing if workload evidence warrants it, and product validation with real target users.

## 14. What did you personally build?
**Answer framework:** “I independently developed [specific modules], using [specific technologies]. The evidence is [paths/tests/commits]. I have verified [exact commands/results]. I have not yet verified [limitations].” Never claim authorship of generated or third-party work that you cannot explain.

## 15. How does this relate to your eight-month experience?
**Answer:** “My eight-month experience is a separate historical claim supported by [certificate, dates, task records and supervisor confirmation]. PortfolioPulse is an independent project built to demonstrate and deepen my backend engineering capability. I do not present it as the system I built during that internship.”

## Oral defence exercise
For each answer:
1. Explain it without reading.
2. Point to the relevant code.
3. Show a test or reproducible request.
4. State one trade-off.
5. State one limitation.
If you cannot do all five, mark the topic as “needs deeper understanding” and study it before using it as a strong interview claim.
