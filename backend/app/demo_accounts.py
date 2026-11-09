from sqlalchemy import Connection, text

DEMO_ORGANIZATION_SLUG = "demo-portfolio"

DEMO_EMAIL_MIGRATIONS = {
    "admin@portfoliopulse.local": "admin@portfoliopulse.example.com",
    "analyst@portfoliopulse.local": "analyst@portfoliopulse.example.com",
    "viewer@portfoliopulse.local": "viewer@portfoliopulse.example.com",
}


def migrate_demo_account_emails(
    connection: Connection,
    email_migrations: dict[str, str] = DEMO_EMAIL_MIGRATIONS,
) -> None:
    for old_email, new_email in email_migrations.items():
        conflicting_user = connection.execute(
            text(
                """
                SELECT old_user.id
                FROM users AS old_user
                JOIN organizations AS demo_organization
                  ON demo_organization.id = old_user.organization_id
                 AND demo_organization.slug = :organization_slug
                JOIN users AS new_user
                  ON new_user.organization_id = old_user.organization_id
                 AND new_user.email = :new_email
                 AND new_user.id != old_user.id
                WHERE old_user.email = :old_email
                LIMIT 1
                """
            ),
            {
                "old_email": old_email,
                "new_email": new_email,
                "organization_slug": DEMO_ORGANIZATION_SLUG,
            },
        ).first()
        if conflicting_user:
            raise RuntimeError(
                f"Cannot migrate {old_email}: {new_email} already exists in the same organization."
            )

        connection.execute(
            text(
                """
                UPDATE users
                SET email = :new_email
                WHERE email = :old_email
                  AND organization_id IN (
                    SELECT id FROM organizations WHERE slug = :organization_slug
                  )
                """
            ),
            {
                "old_email": old_email,
                "new_email": new_email,
                "organization_slug": DEMO_ORGANIZATION_SLUG,
            },
        )
