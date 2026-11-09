import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Organization, User
from app.reporting_templates import create_template
from app.security import hash_password


@pytest.fixture()
def db_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    db = testing_session()
    organization = Organization(name="Test Org", slug="test-org")
    db.add(organization)
    db.flush()
    db.add(
        User(
            organization_id=organization.id,
            full_name="Admin",
            email="admin@example.com",
            password_hash=hash_password("TestPassword123!"),
            role="admin",
        )
    )
    demo_password_hash = hash_password("ChangeMe123!")
    for role, email, full_name in [
        ("admin", "admin@portfoliopulse.example.com", "Demo Administrator"),
        ("analyst", "analyst@portfoliopulse.example.com", "Demo Analyst"),
        ("viewer", "viewer@portfoliopulse.example.com", "Demo Viewer"),
    ]:
        db.add(
            User(
                organization_id=organization.id,
                full_name=full_name,
                email=email,
                password_hash=demo_password_hash,
                role=role,
            )
        )
    db.commit()
    admin = db.query(User).filter(User.email == "admin@example.com").one()
    create_template(
        db,
        organization.id,
        admin,
        "Standard",
        "Default test reporting template",
        [
                {
                    "metric_key": "revenue",
                    "label": "Revenue",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 0,
                },
                {
                    "metric_key": "expenses",
                    "label": "Expenses",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 1,
                },
                {
                    "metric_key": "customer_count",
                    "label": "Customers",
                    "data_type": "integer",
                    "unit": "people",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 2,
                },
                {
                    "metric_key": "new_customers",
                    "label": "New customers",
                    "data_type": "integer",
                    "unit": "people",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 3,
                },
                {
                    "metric_key": "employee_count",
                    "label": "Employees",
                    "data_type": "integer",
                    "unit": "people",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 4,
                },
                {
                    "metric_key": "cash_balance",
                    "label": "Cash balance",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "maximum_value": None,
                    "sort_order": 5,
                },
        ],
    )
    db.commit()
    db.close()
    yield testing_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session_factory):
    def override_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def token(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "TestPassword123!"},
    )
    return r.json()["access_token"]
