import pytest
from app.core.config import Settings
from app.db.base import Base
from app.demo_accounts import migrate_demo_account_emails
from app.models import Organization, ReportingPeriod, User
from app.security import hash_password, verify_password
from scripts import seed_demo_data
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker


def test_demo_email_migration_is_idempotent_and_preserves_user_data():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    accounts = [
        ("existing-admin", "admin", "admin@portfoliopulse.local", False),
        ("existing-analyst", "analyst", "analyst@portfoliopulse.local", True),
        ("existing-viewer", "viewer", "viewer@portfoliopulse.local", True),
    ]
    expected_password_hashes = {
        email: hash_password(f"Existing-{role}-Password-123!")
        for _, role, email, _ in accounts
    }

    with engine.begin() as connection:
        organization = Organization(
            id="org-existing", name="Existing", slug="demo-portfolio"
        )
        unrelated_organization = Organization(
            id="org-unrelated", name="Unrelated", slug="unrelated"
        )
        connection.execute(
            Organization.__table__.insert(),
            [
                {"id": organization.id, "name": organization.name, "slug": organization.slug},
                {
                    "id": unrelated_organization.id,
                    "name": unrelated_organization.name,
                    "slug": unrelated_organization.slug,
                },
            ],
        )
        connection.execute(
            User.__table__.insert(),
            [
                {
                    "id": user_id,
                    "organization_id": organization.id,
                    "full_name": f"Existing {role.title()}",
                    "email": email,
                    "password_hash": expected_password_hashes[email],
                    "role": role,
                    "is_active": is_active,
                }
                for user_id, role, email, is_active in accounts
            ],
        )
        connection.execute(
            User.__table__.insert().values(
                id="user-unrelated",
                organization_id=unrelated_organization.id,
                full_name="Unrelated User",
                email="viewer@portfoliopulse.local",
                password_hash="unrelated-hash",
                role="viewer",
            )
        )

        migrate_demo_account_emails(connection)
        migrate_demo_account_emails(connection)

        account_count = connection.execute(
            select(func.count()).select_from(User.__table__)
        ).scalar_one()
        unrelated_email = connection.execute(
            select(User.email).where(User.id == "user-unrelated")
        ).scalar_one()
        migrated_accounts = {
            user_id: connection.execute(
                select(User.__table__).where(User.id == user_id)
            ).mappings().one()
            for user_id, _, _, _ in accounts
        }

    assert account_count == 4
    assert unrelated_email == "viewer@portfoliopulse.local"
    for user_id, role, old_email, is_active in accounts:
        migrated = migrated_accounts[user_id]
        assert migrated["email"] == old_email.replace(
            "portfoliopulse.local", "portfoliopulse.example.com"
        )
        assert migrated["id"] == user_id
        assert migrated["organization_id"] == "org-existing"
        assert migrated["full_name"] == f"Existing {role.title()}"
        assert migrated["role"] == role
        assert migrated["is_active"] is is_active
        assert migrated["password_hash"] == expected_password_hashes[old_email]
    engine.dispose()


def test_demo_email_migration_refuses_conflict_without_modifying_users():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            Organization.__table__.insert().values(
                id="org-conflict", name="Conflict", slug="demo-portfolio"
            )
        )
        connection.execute(
            User.__table__.insert(),
            [
                {
                    "id": "legacy",
                    "organization_id": "org-conflict",
                    "full_name": "Legacy",
                    "email": "admin@portfoliopulse.local",
                    "password_hash": "legacy-hash",
                    "role": "admin",
                },
                {
                    "id": "current",
                    "organization_id": "org-conflict",
                    "full_name": "Current",
                    "email": "admin@portfoliopulse.example.com",
                    "password_hash": "current-hash",
                    "role": "viewer",
                },
            ],
        )

        try:
            migrate_demo_account_emails(connection)
        except RuntimeError as error:
            assert "already exists in the same organization" in str(error)
        else:
            raise AssertionError("Expected conflicting demo accounts to be rejected")

        emails = connection.execute(
            select(User.email).order_by(User.id)
        ).scalars().all()

    assert emails == ["admin@portfoliopulse.example.com", "admin@portfoliopulse.local"]
    engine.dispose()


def test_seed_is_idempotent_and_preserves_existing_demo_password(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    with testing_session.begin() as session:
        organization = Organization(
            id="demo-org",
            name="Demo Portfolio Organisation",
            slug="demo-portfolio",
        )
        session.add(organization)
        existing_hash = hash_password("ExistingPassword123!")
        session.add(
            User(
                id="existing-admin",
                organization_id=organization.id,
                full_name="Demo Administrator",
                email="admin@portfoliopulse.local",
                password_hash=existing_hash,
                role="admin",
            )
        )

    monkeypatch.setattr(seed_demo_data, "SessionLocal", testing_session)
    monkeypatch.setattr(
        seed_demo_data,
        "settings",
        Settings(
            _env_file=None,
            environment="development",
            enable_demo_seeding=True,
        ),
    )
    seed_demo_data.main()
    seed_demo_data.main()

    with testing_session() as session:
        demo_users = session.scalars(
            select(User).where(User.organization_id == "demo-org")
        ).all()
        by_email = {user.email: user for user in demo_users}
        assert len(demo_users) == 3
        assert by_email["admin@portfoliopulse.example.com"].id == "existing-admin"
        assert by_email["admin@portfoliopulse.example.com"].password_hash == existing_hash
        assert verify_password(
            seed_demo_data.settings.demo_password,
            by_email["analyst@portfoliopulse.example.com"].password_hash,
        )
        assert verify_password(
            seed_demo_data.settings.demo_password,
            by_email["viewer@portfoliopulse.example.com"].password_hash,
        )
        assert set(by_email) == {
            "admin@portfoliopulse.example.com",
            "analyst@portfoliopulse.example.com",
            "viewer@portfoliopulse.example.com",
        }
        seeded_periods = {
            (period.year, period.month): period
            for period in session.scalars(
                select(ReportingPeriod).where(
                    ReportingPeriod.organization_id == "demo-org"
                )
            ).all()
        }
        assert seeded_periods[(2025, 1)].end_date.isoformat() == "2025-01-31"
        assert seeded_periods[(2025, 2)].end_date.isoformat() == "2025-02-28"
        assert seeded_periods[(2025, 4)].end_date.isoformat() == "2025-04-30"

    engine.dispose()


def test_seed_command_rejects_production_before_opening_database(monkeypatch):
    class ProductionConfig:
        environment = "production"
        enable_demo_seeding = False

    monkeypatch.setattr(seed_demo_data, "settings", ProductionConfig())
    monkeypatch.setattr(
        seed_demo_data,
        "SessionLocal",
        lambda: pytest.fail("The seed command must stop before database access."),
    )

    with pytest.raises(RuntimeError, match="only in development"):
        seed_demo_data.main()
