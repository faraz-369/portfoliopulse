from datetime import date
from decimal import Decimal

from app.models import (
    AuditLog,
    Company,
    CompanyMetric,
    Organization,
    ProcessingLog,
    ReportSubmission,
    ReportingPeriod,
    User,
)
from app.security import hash_password
from tests.conftest import token


def create_foreign_tenant(db_session_factory):
    with db_session_factory.begin() as db:
        organization = Organization(name="Other Org", slug="other-org")
        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            full_name="Other Admin",
            email="other-admin@example.com",
            password_hash=hash_password("OtherPassword123!"),
            role="admin",
        )
        db.flush()
        from app.reporting_templates import create_template

        template = create_template(
            db,
            organization.id,
            user,
            "Other Standard",
            None,
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
                }
            ],
        )
        company = Company(
            organization_id=organization.id,
            identifier="OTHER-1",
            slug="other-1",
            name="Other Company",
            industry="SaaS",
        )
        period = ReportingPeriod(
            organization_id=organization.id,
            template_id=template.id,
            year=2026,
            month=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        db.add_all([user, company, period])
        db.flush()

        submission = ReportSubmission(
            organization_id=organization.id,
            company_id=company.id,
            reporting_period_id=period.id,
            template_id=template.id,
            original_filename="other.csv",
            file_checksum="other-tenant-checksum",
            file_size=10,
            submission_status="approved",
            submitted_by=user.id,
            total_rows=1,
            valid_rows=1,
        )
        db.add(submission)
        db.flush()
        db.add_all(
            [
                CompanyMetric(
                    organization_id=organization.id,
                    company_id=company.id,
                    reporting_period_id=period.id,
                    report_submission_id=submission.id,
                    revenue=Decimal("1000.00"),
                    expenses=Decimal("400.00"),
                    customer_count=10,
                    new_customers=2,
                    employee_count=3,
                    cash_balance=Decimal("500.00"),
                ),
                ProcessingLog(
                    organization_id=organization.id,
                    submission_id=submission.id,
                    event_type="validation_errors",
                    message="Foreign tenant validation result",
                    details_json={"errors": [{"message": "foreign error"}]},
                ),
                AuditLog(
                    organization_id=organization.id,
                    user_id=user.id,
                    action="foreign_action",
                    entity_type="company",
                    entity_id=company.id,
                ),
            ]
        )
        return {
            "organization_id": organization.id,
            "company_id": company.id,
            "period_id": period.id,
            "submission_id": submission.id,
        }


def test_tenant_scoped_routes_hide_foreign_resources(client, db_session_factory):
    foreign = create_foreign_tenant(db_session_factory)
    headers = {"Authorization": f"Bearer {token(client)}"}

    companies = client.get("/api/v1/companies", headers=headers)
    periods = client.get("/api/v1/reporting-periods", headers=headers)
    reports = client.get("/api/v1/reports", headers=headers)
    portfolio = client.get("/api/v1/analytics/portfolio/overview", headers=headers)

    assert companies.status_code == 200
    assert all(row["id"] != foreign["company_id"] for row in companies.json())
    assert periods.status_code == 200
    assert all(row["id"] != foreign["period_id"] for row in periods.json())
    assert reports.status_code == 200
    assert all(row["id"] != foreign["submission_id"] for row in reports.json())
    assert portfolio.status_code == 200
    assert portfolio.json()["active_companies"] == 0
    assert portfolio.json()["submitted_reports"] == 0
    assert portfolio.json()["total_revenue"] is None
    assert portfolio.json()["total_customers"] is None


def test_tenant_scoped_resource_routes_reject_foreign_ids(client, db_session_factory):
    foreign = create_foreign_tenant(db_session_factory)
    headers = {"Authorization": f"Bearer {token(client)}"}
    company_payload = {
        "identifier": "CHANGED",
        "name": "Changed Company",
        "industry": "SaaS",
    }

    responses = [
        client.get(f"/api/v1/companies/{foreign['company_id']}", headers=headers),
        client.patch(
            f"/api/v1/companies/{foreign['company_id']}",
            headers=headers,
            json=company_payload,
        ),
        client.delete(f"/api/v1/companies/{foreign['company_id']}", headers=headers),
        client.get(f"/api/v1/reports/{foreign['submission_id']}", headers=headers),
        client.get(
            f"/api/v1/reports/{foreign['submission_id']}/errors", headers=headers
        ),
        client.get(f"/api/v1/reports/{foreign['submission_id']}/logs", headers=headers),
        client.get(
            f"/api/v1/analytics/companies/{foreign['company_id']}/overview",
            headers=headers,
        ),
        client.get(
            f"/api/v1/analytics/companies/{foreign['company_id']}/trends",
            headers=headers,
        ),
    ]

    assert [response.status_code for response in responses] == [404] * len(responses)


def test_tenant_scoped_logs_exclude_foreign_entries(client, db_session_factory):
    create_foreign_tenant(db_session_factory)
    headers = {"Authorization": f"Bearer {token(client)}"}

    audit_logs = client.get("/api/v1/audit-logs", headers=headers)
    processing_logs = client.get("/api/v1/processing-logs", headers=headers)

    assert audit_logs.status_code == 200
    assert all(log["action"] != "foreign_action" for log in audit_logs.json())
    assert processing_logs.status_code == 200
    assert all(
        log["details_json"] != {"errors": [{"message": "foreign error"}]}
        for log in processing_logs.json()
    )


def test_upload_cannot_resolve_foreign_company_or_period(client, db_session_factory):
    create_foreign_tenant(db_session_factory)
    headers = {"Authorization": f"Bearer {token(client)}"}
    csv_bytes = (
        "company_identifier,reporting_year,reporting_month,revenue,expenses,"
        "customer_count,new_customers,employee_count,cash_balance\n"
        "OTHER-1,2026,1,100,40,5,1,2,60\n"
    ).encode()

    response = client.post(
        "/api/v1/reports/upload",
        headers=headers,
        files={"file": ("foreign.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 422
    assert any(error["rule"] == "company_exists" for error in response.json()["errors"])
    assert all(
        error["rule"] != "period_registered" for error in response.json()["errors"]
    )
