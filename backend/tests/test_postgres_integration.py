import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url

from app.db.base import Base
from app.models import (
    Company,
    CompanyMetric,
    Organization,
    ReportSubmission,
    ReportingPeriod,
    ReportingTemplate,
    TemplateMetric,
    User,
)
from app.processing import ingest
from app.security import hash_password


@pytest.fixture()
def postgres_session():
    url_value = os.getenv("PORTFOLIOPULSE_TEST_DATABASE_URL")
    if not url_value:
        pytest.skip("Set PORTFOLIOPULSE_TEST_DATABASE_URL to run PostgreSQL integration tests")
    url = make_url(url_value)
    if not url.database or not url.database.lower().endswith("_test"):
        pytest.fail("PostgreSQL integration tests require a database name ending in '_test'")

    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def build_tenant(session: Session, name: str):
    organization = Organization(name=name, slug=name.lower().replace(" ", "-"))
    session.add(organization)
    session.flush()
    user = User(
        organization_id=organization.id,
        full_name=f"{name} Admin",
        email=f"{organization.slug}@example.com",
        password_hash=hash_password("IntegrationPassword123!"),
        role="admin",
    )
    session.add(user)
    session.flush()
    template = ReportingTemplate(
        organization_id=organization.id,
        name="Monthly",
        version=1,
        is_active=True,
        created_by=user.id,
    )
    session.add(template)
    session.flush()
    session.add(
        TemplateMetric(
            organization_id=organization.id,
            template_id=template.id,
            metric_key="revenue",
            label="Revenue",
            data_type="decimal",
            unit="currency",
            is_required=True,
            minimum_value=Decimal("0"),
            sort_order=0,
        )
    )
    company = Company(
        organization_id=organization.id,
        identifier="COMPANY-1",
        slug=f"{organization.slug}-company-1",
        name=f"{name} Company",
        industry="SaaS",
    )
    session.add(company)
    period = ReportingPeriod(
        organization_id=organization.id,
        template_id=template.id,
        year=2027,
        month=1,
        start_date=date(2027, 1, 1),
        end_date=date(2027, 1, 31),
    )
    session.add(period)
    session.flush()
    return organization, user, template, company, period


def make_submission(organization, user, template, company, period, checksum):
    return ReportSubmission(
        organization_id=organization.id,
        company_id=company.id,
        reporting_period_id=period.id,
        template_id=template.id,
        original_filename="integration.csv",
        file_checksum=checksum,
        file_size=20,
        submission_status="approved",
        submitted_by=user.id,
        total_rows=1,
        valid_rows=1,
    )


def test_postgres_enforces_template_and_company_tenant_relationships(postgres_session):
    session = postgres_session
    tenant_a = build_tenant(session, "Tenant A")
    tenant_b = build_tenant(session, "Tenant B")
    session.commit()

    organization_a, user_a, template_a, company_a, period_a = tenant_a
    organization_b, _, _, company_b, _ = tenant_b

    invalid_period = ReportingPeriod(
        organization_id=organization_a.id,
        template_id=tenant_b[2].id,
        year=2027,
        month=2,
        start_date=date(2027, 2, 1),
        end_date=date(2027, 2, 28),
    )
    session.add(invalid_period)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    organization_a, user_a, template_a, company_a, period_a = build_tenant(
        session, "Tenant A Retry"
    )
    session.commit()
    session.add(
        make_submission(
            organization_a,
            user_a,
            template_a,
            company_b,
            period_a,
            "cross-tenant-company",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_postgres_rejects_metric_that_does_not_match_submission_context(postgres_session):
    session = postgres_session
    tenant = build_tenant(session, "Metric Tenant")
    other_tenant = build_tenant(session, "Other Metric Tenant")
    session.commit()
    organization, user, template, company, period = tenant
    other_company = other_tenant[3]
    submission = make_submission(
        organization, user, template, company, period, "metric-context"
    )
    session.add(submission)
    session.flush()
    session.add(
        CompanyMetric(
            organization_id=organization.id,
            company_id=other_company.id,
            reporting_period_id=period.id,
            report_submission_id=submission.id,
            revenue=Decimal("100.00"),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_postgres_allows_only_one_approved_submission_per_company_period(
    postgres_session,
):
    session = postgres_session
    organization, user, template, company, period = build_tenant(
        session, "Approval Tenant"
    )
    first = make_submission(
        organization, user, template, company, period, "approved-first"
    )
    session.add(first)
    session.commit()

    second = make_submission(
        organization, user, template, company, period, "approved-second"
    )
    session.add(second)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
    assert session.scalar(
        select(ReportSubmission).where(
            ReportSubmission.id == first.id,
            ReportSubmission.submission_status == "approved",
        )
    )


def test_postgres_transaction_rollback_removes_staged_report_metrics(postgres_session):
    session = postgres_session
    organization, user, template, company, period = build_tenant(
        session, "Rollback Tenant"
    )
    submission = make_submission(
        organization, user, template, company, period, "rollback-submission"
    )
    session.add(submission)
    session.flush()
    session.add(
        CompanyMetric(
            organization_id=organization.id,
            company_id=company.id,
            reporting_period_id=period.id,
            report_submission_id=submission.id,
            revenue=Decimal("75.00"),
        )
    )
    session.rollback()
    assert session.scalar(
        select(ReportSubmission).where(
            ReportSubmission.file_checksum == "rollback-submission"
        )
    ) is None
    assert session.scalar(
        select(CompanyMetric).where(CompanyMetric.revenue == Decimal("75.00"))
    ) is None


def test_postgres_ingestion_persists_submission_context_before_metrics(postgres_session):
    session = postgres_session
    organization, user, template, company, period = build_tenant(
        session, "Ingestion Tenant"
    )
    session.commit()
    content = (
        "company_identifier,reporting_year,reporting_month,revenue\n"
        f"{company.identifier},2027,1,125.50\n"
    ).encode()

    submission, errors, replay = ingest(
        content,
        "postgres-integration.csv",
        user,
        session,
        1024 * 1024,
        template_id=template.id,
    )

    assert not replay
    assert errors == []
    assert submission.submission_status == "pending_review"
    assert submission.company_id == company.id
    assert submission.reporting_period_id == period.id
    metric = session.scalar(
        select(CompanyMetric).where(
            CompanyMetric.report_submission_id == submission.id
        )
    )
    assert metric is not None
    assert metric.revenue == Decimal("125.50")
