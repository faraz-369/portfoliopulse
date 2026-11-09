from tests.conftest import token


def test_demo_accounts_can_log_in(client):
    for role, email in [
        ("admin", "admin@portfoliopulse.example.com"),
        ("analyst", "analyst@portfoliopulse.example.com"),
        ("viewer", "viewer@portfoliopulse.example.com"),
    ]:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "ChangeMe123!"},
        )
        assert response.status_code == 200
        access_token = response.json()["access_token"]
        current_user = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert current_user.status_code == 200
        assert current_user.json()["email"] == email
        assert current_user.json()["role"] == role


def test_invalid_demo_password_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@portfoliopulse.example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401


def test_unknown_email_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 401


def test_invalid_email_returns_422(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "ChangeMe123!"},
    )
    assert response.status_code == 422


def test_demo_admin_auth_me_returns_correct_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@portfoliopulse.example.com", "password": "ChangeMe123!"},
    )
    token = response.json()["access_token"]
    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["email"] == "admin@portfoliopulse.example.com"
    assert current_user.json()["full_name"] == "Demo Administrator"
    assert current_user.json()["role"] == "admin"


def test_health(client):
    assert client.get("/health").json()["status"] == "alive"


def test_login_and_me(client):
    t = token(client)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_company_create_and_tenant_scoped_lookup(client):
    t = token(client)
    h = {"Authorization": f"Bearer {t}"}
    r = client.post(
        "/api/v1/companies",
        headers=h,
        json={"identifier": "TEST-1", "name": "Test Company", "industry": "SaaS"},
    )
    assert r.status_code == 200
    assert (
        client.get("/api/v1/companies/" + r.json()["id"], headers=h).status_code == 200
    )
    assert client.get("/api/v1/companies/not-a-real-id", headers=h).status_code == 404


def test_reporting_period_uses_actual_calendar_month_end(client):
    headers = {"Authorization": f"Bearer {token(client)}"}
    response = client.post(
        "/api/v1/reporting-periods", headers=headers, json={"year": 2024, "month": 2}
    )
    assert response.status_code == 200
    assert response.json()["start_date"] == "2024-02-01"
    assert response.json()["end_date"] == "2024-02-29"


def test_reporting_period_bounds_cover_common_and_leap_months(client):
    headers = {"Authorization": f"Bearer {token(client)}"}
    for year, month, expected_end in [
        (2025, 2, "2025-02-28"),
        (2024, 2, "2024-02-29"),
        (2025, 4, "2025-04-30"),
        (2025, 1, "2025-01-31"),
    ]:
        response = client.post(
            "/api/v1/reporting-periods",
            headers=headers,
            json={"year": year, "month": month},
        )
        assert response.status_code == 200
        assert response.json()["start_date"] == f"{year:04d}-{month:02d}-01"
        assert response.json()["end_date"] == expected_end


def test_password_change_uses_json_body_and_new_password_authenticates(client):
    headers = {"Authorization": f"Bearer {token(client)}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "TestPassword123!",
            "new_password": "A-New-Long-Password-123!",
        },
    )
    assert changed.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "A-New-Long-Password-123!"},
    )
    assert login.status_code == 200


def test_template_versions_preserve_period_template_history(client):
    headers = {"Authorization": f"Bearer {token(client)}"}
    template = client.post(
        "/api/v1/reporting-templates",
        headers=headers,
        json={
            "name": "Cash Reporting",
            "description": "Original definition",
            "metrics": [
                {
                    "metric_key": "cash_balance",
                    "label": "Cash",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "sort_order": 0,
                }
            ],
        },
    )
    assert template.status_code == 201
    first = template.json()

    period = client.post(
        "/api/v1/reporting-periods",
        headers=headers,
        json={"year": 2027, "month": 1, "template_id": first["id"]},
    )
    assert period.status_code == 200
    assert period.json()["template_id"] == first["id"]

    version = client.post(
        f"/api/v1/reporting-templates/{first['id']}/versions",
        headers=headers,
        json={
            "description": "Updated definition",
            "metrics": [
                {
                    "metric_key": "cash_balance",
                    "label": "Closing cash balance",
                    "data_type": "decimal",
                    "unit": "currency",
                    "is_required": True,
                    "minimum_value": 0,
                    "sort_order": 0,
                }
            ],
        },
    )
    assert version.status_code == 201
    second = version.json()
    assert second["version"] == first["version"] + 1
    assert second["is_active"] is True
    assert second["metrics"][0]["label"] == "Closing cash balance"

    templates = client.get("/api/v1/reporting-templates", headers=headers).json()
    assert next(item for item in templates if item["id"] == first["id"])[
        "is_active"
    ] is False
    periods = client.get("/api/v1/reporting-periods", headers=headers).json()
    assert next(item for item in periods if item["id"] == period.json()["id"])[
        "template_id"
    ] == first["id"]
