from datetime import date
from html import escape

import pandas as pd
import streamlit as st

from api_client import APIConnectionError, request

st.set_page_config(
    page_title="PortfolioPulse",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)

METRICS = {
    "revenue": ("Revenue", "decimal", "currency"),
    "expenses": ("Expenses", "decimal", "currency"),
    "customer_count": ("Customers", "integer", "people"),
    "new_customers": ("New customers", "integer", "people"),
    "employee_count": ("Employees", "integer", "people"),
    "cash_balance": ("Cash balance", "decimal", "currency"),
}
IDENTITY_COLUMNS = ["company_identifier", "reporting_year", "reporting_month"]
PAGE_INFO = {
    "Overview": "A current view of portfolio reporting and review activity.",
    "Portfolio companies": "Manage the companies in your organisation's portfolio.",
    "Reporting": "Configure reporting requirements and reporting periods.",
    "Submissions": "Validate incoming reports and manage review decisions.",
    "Analytics": "Explore portfolio results sourced from approved reports.",
    "Processing history": "Inspect recent import and validation activity.",
    "Audit history": "Review organisation-level administrative activity.",
    "Account settings": "Manage your account and view organisation context.",
}


def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --pp-ink: #17212f;
            --pp-muted: #687587;
            --pp-line: #e4e9ef;
            --pp-navy: #18324b;
            --pp-blue: #2867a5;
            --pp-paper: #f5f7fa;
        }
        .stApp { background: var(--pp-paper); color: var(--pp-ink); }
        [data-testid="stHeader"] { background: rgba(245,247,250,.94); }
        [data-testid="stSidebar"] {
            background: #fff;
            border-right: 1px solid var(--pp-line);
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--pp-muted);
        }
        .pp-brand {
            display: flex; align-items: center; gap: .7rem;
            padding: .5rem .3rem 1.15rem; margin-bottom: .65rem;
            border-bottom: 1px solid var(--pp-line);
        }
        .pp-mark {
            display: grid; place-items: center; width: 2rem; height: 2rem;
            border-radius: 7px; background: var(--pp-navy); color: #fff;
            font-size: .92rem; font-weight: 700;
        }
        .pp-brand-name { color: var(--pp-ink); font-size: 1rem; font-weight: 700; }
        .pp-brand-sub { color: var(--pp-muted); font-size: .72rem; margin-top: .08rem; }
        .pp-eyebrow {
            color: var(--pp-blue); font-size: .71rem; font-weight: 700;
            letter-spacing: .08em; text-transform: uppercase; margin-bottom: .2rem;
        }
        .pp-page-title { color: var(--pp-ink); font-size: 1.8rem; font-weight: 700; margin: 0; }
        .pp-page-description { color: var(--pp-muted); margin: .25rem 0 1.35rem; }
        .pp-note {
            border-top: 1px solid var(--pp-line); margin-top: 1.2rem; padding-top: .8rem;
            color: var(--pp-muted); font-size: .74rem; line-height: 1.5;
        }
        div[data-testid="stMetric"] {
            background: #fff; border: 1px solid var(--pp-line);
            border-radius: 8px; padding: 1rem 1.1rem;
        }
        div[data-testid="stMetricLabel"] { color: var(--pp-muted); font-size: .82rem; }
        div[data-testid="stMetricValue"] { color: var(--pp-ink); font-size: 1.55rem; }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--pp-line); border-radius: 8px;
        }
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"] {
            background: var(--pp-navy); border-color: var(--pp-navy);
            color: #fff;
        }
        .stButton > button, .stFormSubmitButton > button {
            border-radius: 6px; min-height: 2.45rem;
        }
        [data-testid="stDataFrame"] { border: 1px solid var(--pp-line); border-radius: 7px; }
        @media (max-width: 760px) {
            .pp-page-title { font-size: 1.45rem; }
            [data-testid="stMetricValue"] { font-size: 1.25rem; }
            .pp-brand { padding-bottom: .75rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_call(method, path, token=None, **kwargs):
    try:
        with st.spinner("Connecting to PortfolioPulse..."):
            return request(method, path, token=token, **kwargs)
    except APIConnectionError as exc:
        st.error(str(exc))
        return None


def show_api_error(response, authentication=False):
    if authentication:
        if response.status_code == 401:
            st.error("The email or password was not recognised.")
        elif response.status_code == 422:
            st.error("Enter a valid email address and password.")
        else:
            st.error(f"Sign-in could not be completed (HTTP {response.status_code}).")
        return

    try:
        body = response.json()
    except (ValueError, AttributeError):
        body = {}
    errors = body.get("errors")
    if isinstance(errors, list):
        st.error("The report could not be accepted. Review the validation feedback below.")
        if errors:
            st.dataframe(pd.DataFrame(errors), hide_index=True, use_container_width=True)
        return
    detail = body.get("detail")
    if isinstance(detail, str):
        st.error(detail)
    elif isinstance(detail, list):
        st.error("Some fields need attention.")
        st.dataframe(pd.DataFrame(detail), hide_index=True, use_container_width=True)
    else:
        st.error(f"The request could not be completed (HTTP {response.status_code}).")


def api_json(path, token, **kwargs):
    response = api_call("GET", path, token=token, **kwargs)
    if response is None:
        return None
    if response.status_code == 401:
        st.session_state.token = None
        st.warning("Your session has expired. Sign in again.")
        st.rerun()
    if not response.ok:
        show_api_error(response)
        return None
    return response.json()


def render_page_heading(title, description, organization=None):
    st.markdown('<div class="pp-eyebrow">Portfolio operations</div>', unsafe_allow_html=True)
    st.markdown(
        f'<h1 class="pp-page-title">{escape(title)}</h1>',
        unsafe_allow_html=True,
    )
    context = f" · {escape(organization)}" if organization else ""
    st.markdown(
        f'<div class="pp-page-description">{escape(description)}{context}</div>',
        unsafe_allow_html=True,
    )


def render_table(rows, columns=None, labels=None):
    if not rows:
        return
    frame = pd.DataFrame(rows)
    if columns:
        frame = frame[[column for column in columns if column in frame.columns]]
    if labels:
        frame = frame.rename(columns=labels)
    st.dataframe(frame, hide_index=True, use_container_width=True)


def template_name(template_id, templates):
    template = next((item for item in templates if item["id"] == template_id), None)
    return f"{template['name']} v{template['version']}" if template else "Unavailable template"


def template_metrics(selected, optional):
    return [
        {
            "metric_key": key,
            "label": METRICS[key][0],
            "data_type": METRICS[key][1],
            "unit": METRICS[key][2],
            "is_required": key not in optional,
            "minimum_value": 0,
            "maximum_value": None,
            "sort_order": position,
        }
        for position, key in enumerate(selected)
    ]


def login_screen():
    apply_styles()
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown(
            """
            <div style="padding: 3.2rem 1rem 1rem 0;">
              <div class="pp-brand" style="border:0;">
                <span class="pp-mark">P</span>
                <span><span class="pp-brand-name">PortfolioPulse</span><br>
                <span class="pp-brand-sub">Portfolio operations &amp; intelligence</span></span>
              </div>
              <h1 style="font-size:2.35rem; line-height:1.18; color:#17212f; margin-top:2rem;">
                Reporting clarity<br>across your portfolio.
              </h1>
              <p style="color:#687587; max-width:32rem; line-height:1.7;">
                Collect company performance reports, validate submissions, and review
                approved portfolio results in one place.
              </p>
              <p style="color:#687587; font-size:.8rem; margin-top:2.5rem;">
                Independent demonstration project · Synthetic data
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.write("")
        with st.container(border=True):
            st.subheader("Sign in")
            st.caption("Use your PortfolioPulse account to continue.")
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email address", placeholder="you@organisation.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                response = api_call(
                    "POST",
                    "/auth/login",
                    json={"email": email.strip(), "password": password},
                )
                if response is not None:
                    if response.ok:
                        st.session_state.token = response.json()["access_token"]
                        st.rerun()
                    else:
                        show_api_error(response, authentication=True)
            st.caption("Local demo account details are documented in the project README.")


def overview_page(token, user):
    companies = api_json("/companies", token)
    periods = api_json("/reporting-periods", token)
    reports = api_json("/reports", token)
    if companies is None or periods is None or reports is None:
        return

    staff = user["role"] != "company_submitter"
    analytics = api_json("/analytics/portfolio/overview", token) if staff else None
    pending = sum(report["status"] == "pending_review" for report in reports)
    metrics = [
        ("Portfolio companies", len(companies)),
        ("Reporting periods", len(periods)),
        ("Submitted reports", len(reports)),
        ("Pending review", pending),
    ]
    if user["role"] == "company_submitter":
        metrics[0] = ("Your company", len(companies))
    for column, (label, value) in zip(st.columns(4), metrics):
        column.metric(label, value)

    st.write("")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Recent submissions")
        recent = sorted(
            reports,
            key=lambda item: str(item.get("submitted_at") or ""),
            reverse=True,
        )[:8]
        if recent:
            render_table(
                recent,
                ["filename", "status", "valid_rows", "invalid_rows", "submitted_at"],
                {
                    "filename": "File",
                    "status": "Status",
                    "valid_rows": "Valid rows",
                    "invalid_rows": "Invalid rows",
                    "submitted_at": "Submitted",
                },
            )
        else:
            st.info("No submissions have been recorded.")
    with right:
        st.subheader("Submission status")
        if reports:
            status_counts = pd.Series(
                [item["status"].replace("_", " ").title() for item in reports]
            ).value_counts()
            for label, count in status_counts.items():
                st.progress(
                    int(count) / len(reports),
                    text=f"{label} · {count} of {len(reports)} reports",
                )
        else:
            st.info("Submission activity will appear here after the first report is uploaded.")

    if staff and analytics:
        st.subheader("Approved portfolio results")
        st.caption("Latest approved report per company; reporting periods may differ.")
        money = [
            ("Latest revenue", "total_revenue"),
            ("Latest expenses", "total_expenses"),
            ("Latest profit", "total_profit"),
            ("Active companies", "active_companies"),
        ]
        for column, (label, key) in zip(st.columns(4), money):
            value = analytics.get(key)
            column.metric(label, value if value is not None else "Not reported")
    elif not periods:
        st.info("No reporting periods are configured. An administrator can create one in Reporting.")


def companies_page(token, role):
    search = st.text_input("Search by company name", placeholder="Search companies")
    params = {"status": ""}
    if search.strip():
        params["search"] = search.strip()
    companies = api_json("/companies", token, params=params)
    if companies is None:
        return
    render_table(
        companies,
        ["name", "identifier", "industry", "status", "website", "description"],
        {
            "name": "Company",
            "identifier": "Identifier",
            "industry": "Industry",
            "status": "Status",
            "website": "Website",
            "description": "Description",
        },
    )
    if not companies:
        st.info("No companies match your search. Clear the query or add a company if you are an administrator.")

    if role != "admin":
        return
    with st.expander("Add a portfolio company"):
        with st.form("add_company"):
            identifier = st.text_input("Company identifier")
            name = st.text_input("Company name")
            industry = st.text_input("Industry")
            description = st.text_area("Description (optional)")
            website = st.text_input("Website (optional)")
            submitted = st.form_submit_button("Add company", type="primary")
        if submitted:
            response = api_call(
                "POST",
                "/companies",
                token=token,
                json={
                    "identifier": identifier.strip(),
                    "name": name.strip(),
                    "industry": industry.strip(),
                    "description": description.strip() or None,
                    "website": website.strip() or None,
                },
            )
            if response is not None:
                if response.ok:
                    st.success("Company added to the portfolio.")
                    st.rerun()
                else:
                    show_api_error(response)

    active_companies = [company for company in companies if company["status"] == "active"]
    if active_companies:
        with st.expander("Manage company access"):
            company = st.selectbox(
                "Company",
                active_companies,
                format_func=lambda item: f"{item['name']} ({item['identifier']})",
            )
            with st.form("edit_company"):
                edit_name = st.text_input("Name", value=company["name"])
                edit_industry = st.text_input("Industry", value=company["industry"])
                edit_description = st.text_area(
                    "Description", value=company.get("description") or ""
                )
                edit_website = st.text_input("Website", value=company.get("website") or "")
                save = st.form_submit_button("Save company details")
            if save:
                response = api_call(
                    "PATCH",
                    f"/companies/{company['id']}",
                    token=token,
                    json={
                        "identifier": company["identifier"],
                        "name": edit_name.strip(),
                        "industry": edit_industry.strip(),
                        "description": edit_description.strip() or None,
                        "website": edit_website.strip() or None,
                    },
                )
                if response is not None:
                    if response.ok:
                        st.success("Company details updated.")
                        st.rerun()
                    else:
                        show_api_error(response)

            with st.form("company_submitter"):
                st.markdown("**Create a company submitter**")
                full_name = st.text_input("Submitter name")
                email = st.text_input("Submitter email")
                password = st.text_input("Temporary password", type="password")
                create_submitter = st.form_submit_button("Create submitter account")
            if create_submitter:
                response = api_call(
                    "POST",
                    f"/companies/{company['id']}/submitters",
                    token=token,
                    json={
                        "full_name": full_name.strip(),
                        "email": email.strip(),
                        "password": password,
                    },
                )
                if response is not None:
                    if response.ok:
                        st.success(
                            f"Submitter account created for {response.json()['email']}. "
                            "Share the temporary password securely."
                        )
                    else:
                        show_api_error(response)

    active_company_options = [company for company in companies if company["status"] == "active"]
    if active_company_options:
        with st.expander("Deactivate a company"):
            with st.form("deactivate_company"):
                company = st.selectbox(
                    "Company to deactivate",
                    active_company_options,
                    format_func=lambda item: f"{item['name']} ({item['identifier']})",
                )
                confirm = st.checkbox("I understand this changes the company to inactive.")
                deactivate = st.form_submit_button("Deactivate company")
            if deactivate:
                if not confirm:
                    st.warning("Confirm the action before deactivating this company.")
                else:
                    response = api_call(
                        "DELETE", f"/companies/{company['id']}", token=token
                    )
                    if response is not None:
                        if response.ok:
                            st.success("Company deactivated.")
                            st.rerun()
                        else:
                            show_api_error(response)


def reporting_page(token, role):
    templates = api_json("/reporting-templates", token)
    periods = api_json("/reporting-periods", token)
    if templates is None or periods is None:
        return

    st.subheader("Reporting templates")
    template_rows = [
        {
            "Template": f"{item['name']} v{item['version']}",
            "State": "Active" if item["is_active"] else "Archived",
            "Metrics": ", ".join(
                metric["label"] + ("" if metric["is_required"] else " (optional)")
                for metric in item["metrics"]
            ),
            "Description": item.get("description") or "—",
        }
        for item in templates
    ]
    render_table(template_rows)
    if not templates:
        st.info("No reporting template exists yet. An administrator can create the first template.")

    active_templates = [item for item in templates if item["is_active"]]
    if role == "admin":
        with st.expander("Create a reporting template"):
            with st.form("create_template"):
                name = st.text_input("Template name")
                description = st.text_area("Description (optional)")
                selected = st.multiselect(
                    "Metrics included",
                    list(METRICS),
                    default=["revenue", "expenses", "customer_count"],
                    format_func=lambda key: METRICS[key][0],
                )
                optional = st.multiselect(
                    "Optional metrics",
                    selected,
                    format_func=lambda key: METRICS[key][0],
                )
                create = st.form_submit_button("Create template", type="primary")
            if create:
                if not selected:
                    st.warning("Choose at least one metric.")
                else:
                    response = api_call(
                        "POST",
                        "/reporting-templates",
                        token=token,
                        json={
                            "name": name.strip(),
                            "description": description.strip() or None,
                            "metrics": template_metrics(selected, optional),
                        },
                    )
                    if response is not None:
                        if response.ok:
                            st.success("Reporting template created.")
                            st.rerun()
                        else:
                            show_api_error(response)

        if active_templates:
            with st.expander("Create an immutable template version"):
                selected_template = st.selectbox(
                    "Template to version",
                    active_templates,
                    format_func=lambda item: f"{item['name']} v{item['version']}",
                )
                original_keys = [metric["metric_key"] for metric in selected_template["metrics"]]
                with st.form("create_template_version"):
                    description = st.text_area(
                        "Version description",
                        value=selected_template.get("description") or "",
                    )
                    selected = st.multiselect(
                        "Metrics in the new version",
                        list(METRICS),
                        default=original_keys,
                        format_func=lambda key: METRICS[key][0],
                    )
                    optional = st.multiselect(
                        "Optional metrics in the new version",
                        selected,
                        default=[
                            metric["metric_key"]
                            for metric in selected_template["metrics"]
                            if not metric["is_required"]
                        ],
                        format_func=lambda key: METRICS[key][0],
                    )
                    create_version = st.form_submit_button("Create next version")
                if create_version:
                    if not selected:
                        st.warning("Choose at least one metric.")
                    else:
                        response = api_call(
                            "POST",
                            f"/reporting-templates/{selected_template['id']}/versions",
                            token=token,
                            json={
                                "description": description.strip() or None,
                                "metrics": template_metrics(selected, optional),
                            },
                        )
                        if response is not None:
                            if response.ok:
                                st.success("New template version created. Existing periods are unchanged.")
                                st.rerun()
                            else:
                                show_api_error(response)

    st.divider()
    st.subheader("Reporting periods")
    period_rows = [
        {
            "Period": f"{item['year']}-{item['month']:02d}",
            "From": item["start_date"],
            "To": item["end_date"],
            "Template": template_name(item["template_id"], templates),
            "Status": item["status"].title(),
        }
        for item in periods
    ]
    render_table(period_rows)
    if not periods:
        st.info("No reporting periods have been opened.")

    if role == "admin":
        if active_templates:
            with st.expander("Open a reporting period"):
                with st.form("create_period"):
                    selected_template = st.selectbox(
                        "Template version",
                        active_templates,
                        format_func=lambda item: f"{item['name']} v{item['version']}",
                    )
                    year = st.number_input(
                        "Year", min_value=2000, max_value=2100, value=date.today().year
                    )
                    month = st.selectbox("Month", range(1, 13), format_func=lambda m: f"{m:02d}")
                    create_period = st.form_submit_button("Open reporting period")
                if create_period:
                    response = api_call(
                        "POST",
                        "/reporting-periods",
                        token=token,
                        json={
                            "year": int(year),
                            "month": month,
                            "template_id": selected_template["id"],
                        },
                    )
                    if response is not None:
                        if response.ok:
                            st.success("Reporting period created.")
                            st.rerun()
                        else:
                            show_api_error(response)
        else:
            st.info("Create an active reporting template before opening a period.")


def submissions_page(token, role):
    templates = api_json("/reporting-templates", token)
    periods = api_json("/reporting-periods", token)
    companies = api_json("/companies", token)
    reports = api_json("/reports", token)
    if any(value is None for value in (templates, periods, companies, reports)):
        return

    st.subheader("Submit a company report")
    if role not in {"admin", "analyst", "company_submitter"}:
        st.info("Your account can view submissions but cannot upload reports.")
    elif not periods or not companies:
        st.info("A reporting period and an active company are required before uploading.")
    else:
        period = st.selectbox(
            "Reporting period",
            periods,
            format_func=lambda item: f"{item['year']}-{item['month']:02d} · {template_name(item['template_id'], templates)}",
        )
        template = next(
            (item for item in templates if item["id"] == period["template_id"]), None
        )
        if template is None:
            st.error("The selected reporting period refers to a template that is not available.")
        else:
            company = st.selectbox(
                "Company",
                companies,
                format_func=lambda item: f"{item['name']} ({item['identifier']})",
            )
            csv_columns = IDENTITY_COLUMNS + [
                metric["metric_key"]
                for metric in sorted(template["metrics"], key=lambda item: item["sort_order"])
            ]
            example = (
                ",".join(csv_columns)
                + f"\n{company['identifier']},{period['year']},{period['month']}"
                + ",<value>" * len(template["metrics"])
            )
            st.caption("Use the selected reporting period's exact template columns.")
            st.code(example, language="csv")
            failed = [item for item in reports if item["status"] == "validation_failed"]
            correction = None
            if failed:
                correction = st.selectbox(
                    "Correcting a failed submission (optional)",
                    [None] + failed,
                    format_func=lambda item: (
                        "New report"
                        if item is None
                        else f"{item['filename']} · {item['id'][:8]}"
                    ),
                )
            upload = st.file_uploader("CSV report", type=["csv"], key="report_upload")
            if upload and st.button("Validate and submit", type="primary"):
                data = {"template_id": template["id"]}
                if correction:
                    data["resubmission_of_id"] = correction["id"]
                response = api_call(
                    "POST",
                    "/reports/upload",
                    token=token,
                    data=data,
                    files={"file": (upload.name, upload.getvalue(), "text/csv")},
                )
                if response is not None:
                    try:
                        result = response.json()
                    except ValueError:
                        result = {}
                    if response.ok:
                        st.success(
                            f"Report recorded with status: {result.get('status', 'submitted').replace('_', ' ')}."
                        )
                        st.caption(
                            f"{result.get('valid_rows', 0)} valid · "
                            f"{result.get('invalid_rows', 0)} invalid · "
                            f"{result.get('duplicate_rows', 0)} duplicate rows"
                        )
                        st.rerun()
                    else:
                        show_api_error(response)

    st.divider()
    st.subheader("Submission register")
    report_rows = [
        {
            "File": item["filename"],
            "Status": item["status"].replace("_", " ").title(),
            "Valid rows": item["valid_rows"],
            "Invalid rows": item["invalid_rows"],
            "Submitted": item.get("submitted_at"),
            "Reference": item["id"][:8],
        }
        for item in reports
    ]
    render_table(report_rows)
    if not reports:
        st.info("No submissions have been recorded.")
        return

    selected = st.selectbox(
        "Submission details",
        reports,
        format_func=lambda item: f"{item['filename']} · {item['status'].replace('_', ' ')} · {item['id'][:8]}",
    )
    detail = api_json(f"/reports/{selected['id']}", token)
    if detail is None:
        return
    left, right = st.columns(2)
    left.metric("Current status", detail["status"].replace("_", " ").title())
    right.metric("Rows accepted", f"{detail['valid_rows']} / {detail['total_rows']}")
    st.caption(
        f"Template {template_name(detail['template_id'], templates)}"
        + (
            f" · resubmission of {detail['resubmission_of_id'][:8]}"
            if detail.get("resubmission_of_id")
            else ""
        )
    )

    errors = api_json(f"/reports/{selected['id']}/errors", token)
    if errors:
        st.markdown("**Validation feedback**")
        render_table(errors)
    events = api_json(f"/reports/{selected['id']}/events", token)
    if events:
        st.markdown("**Submission history**")
        render_table(
            events,
            ["created_at", "previous_state", "new_state", "actor_id", "reason"],
            {
                "created_at": "Time",
                "previous_state": "Previous status",
                "new_state": "New status",
                "actor_id": "Actor",
                "reason": "Reason",
            },
        )

    if detail["status"] == "pending_review" and role in {"admin", "analyst"}:
        with st.form(f"review_{selected['id']}"):
            comment = st.text_area("Review note (optional)")
            mark_reviewed = st.form_submit_button("Record review")
        if mark_reviewed:
            response = api_call(
                "POST",
                f"/reports/{selected['id']}/review",
                token=token,
                json={"comment": comment.strip() or None},
            )
            if response is not None:
                if response.ok:
                    st.success("Review recorded.")
                    st.rerun()
                else:
                    show_api_error(response)

    if (
        detail["status"] == "pending_review"
        and detail.get("reviewed_at")
        and role == "admin"
    ):
        with st.form(f"decision_{selected['id']}"):
            decision = st.selectbox("Decision", ["approved", "rejected"])
            reason = st.text_area("Decision reason")
            submit_decision = st.form_submit_button("Save decision", type="primary")
        if submit_decision:
            response = api_call(
                "POST",
                f"/reports/{selected['id']}/decision",
                token=token,
                json={"decision": decision, "reason": reason.strip() or None},
            )
            if response is not None:
                if response.ok:
                    st.success(f"Submission {response.json()['status']}.")
                    st.rerun()
                else:
                    show_api_error(response)


def analytics_page(token, user, periods, companies):
    if user["role"] == "company_submitter":
        company_id = user.get("company_id")
        company = next((item for item in companies if item["id"] == company_id), None)
        if company is None:
            st.info("The company associated with this account is unavailable.")
            return
        st.caption("Company results include approved submissions only.")
        overview = api_json(f"/analytics/companies/{company_id}/overview", token)
        trends = api_json(f"/analytics/companies/{company_id}/trends", token)
        if overview is None or trends is None:
            return
        for column, (label, key) in zip(
            st.columns(4),
            [
                ("Approved periods", "periods"),
                ("Revenue", "revenue"),
                ("Expenses", "expenses"),
                ("Profit", "profit"),
            ],
        ):
            value = overview.get(key)
            column.metric(label, value if value is not None else "Not reported")
        if trends:
            period_labels = {
                item["id"]: f"{item['year']}-{item['month']:02d}" for item in periods
            }
            frame = pd.DataFrame(
                [
                    {
                        "Period": period_labels.get(item["period_id"], "Unknown"),
                        "Revenue": float(item["revenue"]) if item["revenue"] is not None else None,
                        "Expenses": float(item["expenses"]) if item["expenses"] is not None else None,
                        "Profit": float(item["profit"]) if item["profit"] is not None else None,
                    }
                    for item in trends
                ]
            ).set_index("Period")
            st.subheader("Approved financial trend")
            st.line_chart(frame, color=["#2867a5", "#a9b5c3", "#3b816d"])
        else:
            st.info("Approved trend data will appear when a report is approved.")
        return

    overview = api_json("/analytics/portfolio/overview", token)
    if overview is None:
        return
    st.caption("Only the latest approved report per company is included; reporting periods can differ.")
    fields = [
        ("Active companies", "active_companies"),
        ("Latest revenue", "total_revenue"),
        ("Latest expenses", "total_expenses"),
        ("Latest profit", "total_profit"),
        ("Customers", "total_customers"),
        ("Employees", "total_employees"),
        ("Cash balance", "total_cash_balance"),
        ("Submitted reports", "submitted_reports"),
    ]
    for start in range(0, len(fields), 4):
        for column, (label, key) in zip(
            st.columns(4),
            fields[start : start + 4],
        ):
            value = overview.get(key)
            column.metric(label, value if value is not None else "Not reported")

    st.subheader("Metric coverage")
    coverage = overview.get("metric_coverage") or {}
    active_companies = max(overview.get("active_companies") or 0, 1)
    for key, (label, _, _) in METRICS.items():
        count = coverage.get(key, 0)
        st.progress(
            min(count / active_companies, 1.0),
            text=f"{label} · {count} of {overview.get('active_companies') or 0} active companies",
        )
    periods_in_data = overview.get("latest_reporting_periods") or []
    if periods_in_data:
        st.caption(
            "Latest approved reporting periods: "
            + ", ".join(
                f"{item['year']}-{item['month']:02d} ({item['company_count']} companies)"
                for item in periods_in_data
            )
        )

    st.divider()
    st.subheader("Company performance")
    if companies:
        company = st.selectbox(
            "Company",
            companies,
            format_func=lambda item: f"{item['name']} ({item['identifier']})",
            key="analytics_company",
        )
        result = api_json(f"/analytics/companies/{company['id']}/overview", token)
        trends = api_json(f"/analytics/companies/{company['id']}/trends", token)
        if result is not None:
            st.caption(
                f"{result['periods']} approved reporting periods"
                + (
                    f" · latest {result['latest_reporting_period']['year']}-"
                    f"{result['latest_reporting_period']['month']:02d}"
                    if result.get("latest_reporting_period")
                    else ""
                )
            )
            if trends:
                period_labels = {
                    item["id"]: f"{item['year']}-{item['month']:02d}" for item in periods
                }
                frame = pd.DataFrame(
                    [
                        {
                            "Period": period_labels.get(item["period_id"], "Unknown"),
                            "Revenue": float(item["revenue"]) if item["revenue"] is not None else None,
                            "Expenses": float(item["expenses"]) if item["expenses"] is not None else None,
                            "Profit": float(item["profit"]) if item["profit"] is not None else None,
                        }
                        for item in trends
                    ]
                ).set_index("Period")
                st.line_chart(frame, color=["#2867a5", "#a9b5c3", "#3b816d"])
            else:
                st.info("This company has no approved trend data.")
    else:
        st.info("Add portfolio companies to explore their approved reporting data.")


def activity_page(token, endpoint, columns, labels, empty_message):
    records = api_json(endpoint, token)
    if records is None:
        return
    if not records:
        st.info(empty_message)
        return
    render_table(records, columns, labels)


def account_page(token, user, organization):
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Your account")
        st.write(f"**Name:** {user['full_name']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role'].replace('_', ' ').title()}")
        st.write(f"**Organisation:** {organization.get('name', 'Unavailable')}")
        st.caption("Organisation details are read-only in this application.")
    with right:
        st.subheader("Change password")
        with st.form("change_password"):
            current = st.text_input("Current password", type="password")
            new = st.text_input("New password (minimum 12 characters)", type="password")
            confirmation = st.text_input("Confirm new password", type="password")
            update = st.form_submit_button("Update password", type="primary")
        if update:
            if len(new) < 12:
                st.warning("The new password must be at least 12 characters.")
            elif new != confirmation:
                st.warning("The new password confirmation does not match.")
            else:
                response = api_call(
                    "POST",
                    "/auth/change-password",
                    token=token,
                    json={"current_password": current, "new_password": new},
                )
                if response is not None:
                    if response.ok:
                        st.success("Password updated. Your current session remains active.")
                    else:
                        show_api_error(response)


def run_app():
    apply_styles()
    if "token" not in st.session_state:
        st.session_state.token = None
    if not st.session_state.token:
        login_screen()
        return

    token = st.session_state.token
    current_response = api_call("GET", "/auth/me", token=token)
    if current_response is None:
        return
    if current_response.status_code == 401:
        st.session_state.token = None
        st.warning("Your session has expired. Sign in again.")
        st.rerun()
    if not current_response.ok:
        show_api_error(current_response)
        return
    user = current_response.json()
    organization = api_json("/organizations/me", token)
    if organization is None:
        return

    pages = [
        "Overview",
        "Portfolio companies",
        "Reporting",
        "Submissions",
    ]
    if user["role"] != "company_submitter":
        pages.append("Analytics")
    elif user.get("company_id"):
        pages.append("Analytics")
    if user["role"] in {"admin", "analyst"}:
        pages.append("Processing history")
    if user["role"] == "admin":
        pages.append("Audit history")
    pages.append("Account settings")

    st.sidebar.markdown(
        """
        <div class="pp-brand">
          <span class="pp-mark">P</span>
          <span><span class="pp-brand-name">PortfolioPulse</span><br>
          <span class="pp-brand-sub">Portfolio operations</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption(organization.get("name", "Organisation"))
    if "active_page" not in st.session_state or st.session_state.active_page not in pages:
        st.session_state.active_page = "Overview"
    page = st.sidebar.radio("Workspace", pages, key="active_page")
    st.sidebar.markdown("---")
    st.sidebar.caption(f"{user['full_name']} · {user['role'].replace('_', ' ').title()}")
    st.sidebar.caption(user["email"])
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state.token = None
        st.session_state.pop("active_page", None)
        st.rerun()
    st.sidebar.markdown(
        '<div class="pp-note">Independent demonstration project using synthetic data.</div>',
        unsafe_allow_html=True,
    )

    render_page_heading(page, PAGE_INFO[page], organization.get("name"))
    if page == "Overview":
        overview_page(token, user)
    elif page == "Portfolio companies":
        companies_page(token, user["role"])
    elif page == "Reporting":
        reporting_page(token, user["role"])
    elif page == "Submissions":
        submissions_page(token, user["role"])
    elif page == "Analytics":
        periods = api_json("/reporting-periods", token)
        companies = api_json("/companies", token)
        if periods is not None and companies is not None:
            analytics_page(token, user, periods, companies)
    elif page == "Processing history":
        activity_page(
            token,
            "/processing-logs",
            ["created_at", "event_type", "severity", "message", "submission_id"],
            {
                "created_at": "Time",
                "event_type": "Event",
                "severity": "Level",
                "message": "Activity",
                "submission_id": "Submission",
            },
            "No processing activity is available yet.",
        )
    elif page == "Audit history":
        activity_page(
            token,
            "/audit-logs",
            ["created_at", "user_id", "action", "entity_type", "entity_id"],
            {
                "created_at": "Time",
                "user_id": "User",
                "action": "Action",
                "entity_type": "Record type",
                "entity_id": "Record",
            },
            "No audit events have been recorded yet.",
        )
    elif page == "Account settings":
        account_page(token, user, organization)


run_app()
