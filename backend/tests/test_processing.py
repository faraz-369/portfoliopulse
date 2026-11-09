import csv
import io

from tests.conftest import token

CSV_COLUMNS = [
    "company_identifier",
    "reporting_year",
    "reporting_month",
    "revenue",
    "expenses",
    "customer_count",
    "new_customers",
    "employee_count",
    "cash_balance",
]


def create_company(client, identifier, name):
    headers = {"Authorization": f"Bearer {token(client)}"}
    response = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"identifier": identifier, "name": name, "industry": "SaaS"},
    )
    assert response.status_code == 200
    return response.json()


def create_period(client, year, month):
    headers = {"Authorization": f"Bearer {token(client)}"}
    response = client.post(
        "/api/v1/reporting-periods",
        headers=headers,
        json={"year": year, "month": month},
    )
    assert response.status_code == 200
    return response.json()


def upload_rows(
    client,
    rows,
    filename="metrics.csv",
    email="admin@example.com",
    resubmission_of_id=None,
    password=None,
):
    password = password or (
        "TestPassword123!" if email == "admin@example.com" else "ChangeMe123!"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    data = {"resubmission_of_id": resubmission_of_id} if resubmission_of_id else None
    return client.post(
        "/api/v1/reports/upload",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        data=data,
        files={"file": (filename, output.getvalue().encode(), "text/csv")},
    )


def report_row(
    identifier,
    year,
    month,
    revenue,
    expenses,
    customers,
    new_customers,
    employees,
    cash_balance,
):
    return {
        "company_identifier": identifier,
        "reporting_year": str(year),
        "reporting_month": str(month),
        "revenue": str(revenue),
        "expenses": str(expenses),
        "customer_count": str(customers),
        "new_customers": str(new_customers),
        "employee_count": str(employees),
        "cash_balance": str(cash_balance),
    }


def approve_submission(client, submission_id):
    headers = {"Authorization": f"Bearer {token(client)}"}
    reviewed = client.post(
        f"/api/v1/reports/{submission_id}/review",
        headers=headers,
        json={"comment": "Reviewed against synthetic source"},
    )
    assert reviewed.status_code == 200
    decision = client.post(
        f"/api/v1/reports/{submission_id}/decision",
        headers=headers,
        json={"decision": "approved", "reason": "Synthetic report accepted"},
    )
    assert decision.status_code == 200


def test_valid_upload_is_pending_review_and_identical_retry_is_idempotent(client):
    create_company(client, "ACME-1", "Acme One")
    create_period(client, 2026, 1)
    row = report_row("ACME-1", 2026, 1, "1250.25", "500.10", 12, 3, 4, "800")

    uploaded = upload_rows(client, [row])
    assert uploaded.status_code == 200
    result = uploaded.json()
    assert result["status"] == "pending_review"
    assert result["total_rows"] == 1
    assert result["valid_rows"] == 1
    assert result["invalid_rows"] == 0
    assert result["errors"] == []

    detail = client.get(
        f"/api/v1/reports/{result['submission_id']}",
        headers={"Authorization": f"Bearer {token(client)}"},
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "pending_review"

    duplicate = upload_rows(client, [row])
    assert duplicate.status_code == 200
    assert duplicate.json()["submission_id"] == result["submission_id"]
    assert duplicate.json()["idempotent_replay"] is True


def test_invalid_only_upload_is_saved_with_retrievable_errors(client):
    create_period(client, 2026, 1)
    row = report_row("UNKNOWN", 2026, 1, "-10", "20", 5, 1, 2, "30")

    response = upload_rows(client, [row])
    assert response.status_code == 422
    result = response.json()
    assert result["status"] == "validation_failed"
    assert result["total_rows"] == 1
    assert result["valid_rows"] == 0
    assert result["invalid_rows"] == 1
    assert {error["rule"] for error in result["errors"]} == {
        "company_exists",
        "below_minimum",
    }

    headers = {"Authorization": f"Bearer {token(client)}"}
    detail = client.get(f"/api/v1/reports/{result['submission_id']}", headers=headers)
    errors = client.get(
        f"/api/v1/reports/{result['submission_id']}/errors", headers=headers
    )
    logs = client.get(
        f"/api/v1/reports/{result['submission_id']}/logs", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "validation_failed"
    assert errors.json() == result["errors"]
    assert any(log["event_type"] == "ingestion_failed" for log in logs.json())


def test_partial_upload_persists_valid_row_and_reports_invalid_row(client):
    create_company(client, "ACME-2", "Acme Two")
    create_period(client, 2026, 1)
    valid = report_row("ACME-2", 2026, 1, "100", "40", 8, 2, 3, "60")
    invalid = report_row("UNKNOWN", 2026, 1, "100", "40", 8, 2, 3, "60")

    response = upload_rows(client, [valid, invalid])
    assert response.status_code == 422
    assert response.json()["status"] == "validation_failed"
    assert response.json()["valid_rows"] == 1
    assert response.json()["invalid_rows"] == 1
    assert response.json()["errors"][0]["rule"] == "company_exists"


def test_viewer_cannot_upload_reports(client):
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "viewer@portfoliopulse.example.com",
            "password": "ChangeMe123!",
        },
    )
    assert login.status_code == 200
    response = client.post(
        "/api/v1/reports/upload",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        files={"file": ("empty.csv", b"header\n", "text/csv")},
    )
    assert response.status_code == 403


def test_company_submitter_can_retrieve_own_failure_not_other_company_upload(client):
    headers = {"Authorization": f"Bearer {token(client)}"}
    company_a = create_company(client, "SUBMIT-A", "Submitter A")
    company_b = create_company(client, "SUBMIT-B", "Submitter B")
    create_period(client, 2026, 4)

    users = []
    for company, email in (
        (company_a, "submitter-a@example.com"),
        (company_b, "submitter-b@example.com"),
    ):
        response = client.post(
            f"/api/v1/companies/{company['id']}/submitters",
            headers=headers,
            json={
                "full_name": "Company Submitter",
                "email": email,
                "password": "CompanySubmitter123!",
            },
        )
        assert response.status_code == 201
        users.append(email)

    invalid_row = report_row("SUBMIT-A", 2026, 4, "-5", "20", 5, 1, 2, "30")
    failed = upload_rows(
        client,
        [invalid_row],
        email=users[0],
        filename="submitter-invalid.csv",
        password="CompanySubmitter123!",
    )
    assert failed.status_code == 422
    failed_id = failed.json()["submission_id"]

    submitter_a_login = client.post(
        "/api/v1/auth/login",
        json={"email": users[0], "password": "CompanySubmitter123!"},
    )
    submitter_b_login = client.post(
        "/api/v1/auth/login",
        json={"email": users[1], "password": "CompanySubmitter123!"},
    )
    headers_a = {
        "Authorization": f"Bearer {submitter_a_login.json()['access_token']}"
    }
    headers_b = {
        "Authorization": f"Bearer {submitter_b_login.json()['access_token']}"
    }
    assert any(
        report["id"] == failed_id
        for report in client.get("/api/v1/reports", headers=headers_a).json()
    )
    assert (
        client.get(f"/api/v1/reports/{failed_id}", headers=headers_a).status_code
        == 200
    )
    assert client.get("/api/v1/reports", headers=headers_b).json() == []
    assert (
        client.get(f"/api/v1/reports/{failed_id}", headers=headers_b).status_code
        == 404
    )

    replay = upload_rows(
        client,
        [invalid_row],
        email=users[1],
        filename="submitter-invalid.csv",
        password="CompanySubmitter123!",
    )
    assert replay.status_code == 400
    assert "submission_id" not in replay.json()


def test_portfolio_aggregates_latest_report_per_company(client):
    create_company(client, "ACME-A", "Acme A")
    create_company(client, "ACME-B", "Acme B")
    create_period(client, 2026, 1)
    create_period(client, 2026, 2)

    january_a = upload_rows(
        client,
        [report_row("ACME-A", 2026, 1, 100, 40, 10, 2, 2, 20)],
        filename="a-jan.csv",
    )
    february_a = upload_rows(
        client,
        [report_row("ACME-A", 2026, 2, 200, 70, 12, 3, 3, 30)],
        filename="a-feb.csv",
    )
    january_b = upload_rows(
        client,
        [report_row("ACME-B", 2026, 1, 50, 20, 5, 1, 1, 10)],
        filename="b-jan.csv",
    )
    for submission in (january_a, february_a, january_b):
        assert submission.status_code == 200
        approve_submission(client, submission.json()["submission_id"])

    headers = {"Authorization": f"Bearer {token(client)}"}
    overview = client.get("/api/v1/analytics/portfolio/overview", headers=headers)
    assert overview.status_code == 200
    data = overview.json()
    assert data["reporting_basis"] == "latest_available_report_per_company"
    assert data["periods_may_differ"] is True
    assert data["total_revenue"] == "250.00"
    assert data["total_expenses"] == "90.00"
    assert data["total_profit"] == "160.00"
    assert data["total_customers"] == 17
    assert data["total_employees"] == 4
    assert data["total_cash_balance"] == "40.00"
    assert data["latest_reporting_periods"] == [
        {"year": 2026, "month": 1, "company_count": 1},
        {"year": 2026, "month": 2, "company_count": 1},
    ]

    companies = client.get("/api/v1/companies", headers=headers).json()
    company_a = next(company for company in companies if company["identifier"] == "ACME-A")
    company_overview = client.get(
        f"/api/v1/analytics/companies/{company_a['id']}/overview",
        headers=headers,
    )
    assert company_overview.status_code == 200
    assert company_overview.json()["revenue"] == "300.00"
    assert company_overview.json()["new_customers"] == 5
    assert company_overview.json()["latest_customers"] == 12
    assert company_overview.json()["latest_employees"] == 3
    assert company_overview.json()["latest_cash_balance"] == "30.00"
    assert company_overview.json()["latest_reporting_period"] == {
        "year": 2026,
        "month": 2,
    }


def test_invalid_report_can_be_corrected_reviewed_and_approved(client):
    create_company(client, "LIFECYCLE-1", "Lifecycle Company")
    create_period(client, 2026, 3)
    invalid_row = report_row(
        "LIFECYCLE-1", 2026, 3, "-10", "20", 5, 1, 2, "30"
    )
    invalid = upload_rows(client, [invalid_row], filename="invalid.csv")
    assert invalid.status_code == 422
    failed_id = invalid.json()["submission_id"]
    assert invalid.json()["status"] == "validation_failed"

    corrected_row = report_row(
        "LIFECYCLE-1", 2026, 3, "100", "40", 5, 1, 2, "30"
    )
    corrected = upload_rows(
        client,
        [corrected_row],
        filename="corrected.csv",
        resubmission_of_id=failed_id,
    )
    assert corrected.status_code == 200
    corrected_id = corrected.json()["submission_id"]
    assert corrected.json()["status"] == "pending_review"

    admin_headers = {"Authorization": f"Bearer {token(client)}"}
    before_approval = client.get(
        "/api/v1/analytics/portfolio/overview", headers=admin_headers
    ).json()
    assert before_approval["total_revenue"] is None

    analyst_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst@portfoliopulse.example.com",
            "password": "ChangeMe123!",
        },
    )
    assert analyst_login.status_code == 200
    analyst_headers = {
        "Authorization": f"Bearer {analyst_login.json()['access_token']}"
    }
    reviewed = client.post(
        f"/api/v1/reports/{corrected_id}/review",
        headers=analyst_headers,
        json={"comment": "Corrected figures verified"},
    )
    assert reviewed.status_code == 200

    decision = client.post(
        f"/api/v1/reports/{corrected_id}/decision",
        headers=admin_headers,
        json={"decision": "approved", "reason": "Synthetic report accepted"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    after_approval = client.get(
        "/api/v1/analytics/portfolio/overview", headers=admin_headers
    ).json()
    assert after_approval["total_revenue"] == "100.00"
    assert after_approval["total_profit"] == "60.00"

    events = client.get(
        f"/api/v1/reports/{corrected_id}/events", headers=admin_headers
    )
    assert events.status_code == 200
    assert [event["new_state"] for event in events.json()] == [
        "submitted",
        "processing",
        "pending_review",
        "pending_review",
        "approved",
    ]
    assert events.json()[-1]["reason"] == "Synthetic report accepted"

    audit = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert audit.status_code == 200
    assert any(
        row["entity_id"] == corrected_id
        and row["action"] == "submission_state_changed"
        for row in audit.json()
    )
