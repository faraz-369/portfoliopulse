import csv
import io

from app.models import Organization, User
from app.security import hash_password
from tests.conftest import token


def _csv_content(identifier, year, month, revenue, expenses):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "company_identifier",
            "reporting_year",
            "reporting_month",
            "revenue",
            "expenses",
        ]
    )
    writer.writerow([identifier, year, month, revenue, expenses])
    return output.getvalue().encode()


def _upload(client, headers, template_id, identifier, revenue, expenses, parent=None):
    data = {"template_id": template_id}
    if parent:
        data["resubmission_of_id"] = parent
    content = _csv_content(identifier, 2027, 2, revenue, expenses)
    return client.post(
        "/api/v1/reports/upload",
        headers=headers,
        data=data,
        files={"file": ("synthetic.csv", content, "text/csv")},
    )


def test_complete_synthetic_reporting_lifecycle_is_tenant_scoped(
    client, db_session_factory
):
    admin_headers = {"Authorization": f"Bearer {token(client)}"}
    template = client.post(
        "/api/v1/reporting-templates",
        headers=admin_headers,
        json={
            "name": "Synthetic Demonstration",
            "description": "Synthetic end-to-end lifecycle",
            "metrics": [
                {
                    "metric_key": "revenue",
                    "label": "Revenue",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "sort_order": 0,
                },
                {
                    "metric_key": "expenses",
                    "label": "Expenses",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "sort_order": 1,
                },
            ],
        },
    )
    assert template.status_code == 201
    template_id = template.json()["id"]

    period = client.post(
        "/api/v1/reporting-periods",
        headers=admin_headers,
        json={"year": 2027, "month": 2, "template_id": template_id},
    )
    assert period.status_code == 200

    company_a1 = client.post(
        "/api/v1/companies",
        headers=admin_headers,
        json={"identifier": "DEMO-A1", "name": "Synthetic Company A1", "industry": "SaaS"},
    ).json()
    company_a2 = client.post(
        "/api/v1/companies",
        headers=admin_headers,
        json={"identifier": "DEMO-A2", "name": "Synthetic Company A2", "industry": "SaaS"},
    ).json()

    first = _upload(
        client, admin_headers, template_id, company_a1["identifier"], "120", "50"
    )
    assert first.status_code == 200
    first_id = first.json()["submission_id"]
    assert first.json()["status"] == "pending_review"

    invalid = _upload(
        client, admin_headers, template_id, company_a2["identifier"], "-10", "20"
    )
    assert invalid.status_code == 422
    assert invalid.json()["status"] == "validation_failed"
    failed_id = invalid.json()["submission_id"]
    assert invalid.json()["errors"][0]["rule"] == "below_minimum"

    corrected = _upload(
        client,
        admin_headers,
        template_id,
        company_a2["identifier"],
        "90",
        "30",
        parent=failed_id,
    )
    assert corrected.status_code == 200
    corrected_id = corrected.json()["submission_id"]
    assert corrected.json()["status"] == "pending_review"

    analyst_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst@portfoliopulse.example.com",
            "password": "ChangeMe123!",
        },
    )
    analyst_headers = {
        "Authorization": f"Bearer {analyst_login.json()['access_token']}"
    }
    for submission_id in (first_id, corrected_id):
        reviewed = client.post(
            f"/api/v1/reports/{submission_id}/review",
            headers=analyst_headers,
            json={"comment": "Synthetic values checked"},
        )
        assert reviewed.status_code == 200
        decision = client.post(
            f"/api/v1/reports/{submission_id}/decision",
            headers=admin_headers,
            json={"decision": "approved", "reason": "Synthetic report accepted"},
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "approved"

    analytics = client.get(
        "/api/v1/analytics/portfolio/overview", headers=admin_headers
    )
    assert analytics.status_code == 200
    assert analytics.json()["total_revenue"] == "210.00"
    assert analytics.json()["total_expenses"] == "80.00"
    assert analytics.json()["total_profit"] == "130.00"
    assert analytics.json()["latest_reporting_periods"] == [
        {"year": 2027, "month": 2, "company_count": 2}
    ]

    history = client.get(
        f"/api/v1/reports/{corrected_id}/events", headers=admin_headers
    )
    assert history.status_code == 200
    assert [event["new_state"] for event in history.json()] == [
        "submitted",
        "processing",
        "pending_review",
        "pending_review",
        "approved",
    ]
    audit = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert audit.status_code == 200
    assert any(event["entity_id"] == corrected_id for event in audit.json())

    with db_session_factory.begin() as db:
        organization_b = Organization(name="Synthetic Organisation B", slug="synthetic-org-b")
        db.add(organization_b)
        db.flush()
        db.add(
            User(
                organization_id=organization_b.id,
                full_name="Organisation B Admin",
                email="org-b-admin@example.com",
                password_hash=hash_password("OrganisationBPassword123!"),
                role="admin",
            )
        )

    login_b = client.post(
        "/api/v1/auth/login",
        json={
            "email": "org-b-admin@example.com",
            "password": "OrganisationBPassword123!",
        },
    )
    assert login_b.status_code == 200
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    assert client.get("/api/v1/reports", headers=headers_b).json() == []
    assert (
        client.get(f"/api/v1/reports/{corrected_id}", headers=headers_b).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/companies/{company_a1['id']}", headers=headers_b).status_code
        == 404
    )
