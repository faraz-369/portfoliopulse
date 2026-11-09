# Security controls and limitations

Implemented: Argon2 password hashing, signed expiring JWTs, role dependencies, tenant-scoped record queries, PostgreSQL composite tenant foreign keys, parameterised SQLAlchemy queries, request schema validation, upload size and extension limits, no stack traces in client errors, configurable CORS, and environment-aware configuration validation. Admins configure templates, periods, companies, submitter accounts, and final report decisions; analysts can upload and review; company submitters are bound to one company; viewers cannot upload or decide reports. Company submitters can read their own unassociated failed submissions, but cannot replay or inspect another company's submission.

In production, `ENVIRONMENT=production` is required. Startup rejects missing or known-default JWT secrets, secrets shorter than 32 characters, missing or non-PostgreSQL database URLs, the local development database password, absent or non-HTTPS CORS origins, demo passwords, and demo-seeding opt-in. Configuration errors identify setting names or requirements only and do not echo secret values. The checked-in `.env.example` and Compose setup are development-only.

Demo data is not created during application startup. The seed command requires `ENVIRONMENT=development` and explicit `ENABLE_DEMO_SEEDING=true`; production configuration rejects that flag. Existing demo accounts are not recreated or given new password hashes by a repeated seed.

Limitations: no refresh-token rotation, MFA, password reset workflow, rate limiting, malware scanning, external penetration test or formal security audit. These checks do not make the application production-certified; deployment infrastructure, operational controls and independent security review remain necessary.
