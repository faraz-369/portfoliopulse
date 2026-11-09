from datetime import date, datetime, timezone
import calendar
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    User,
    Organization,
    Company,
    ReportingPeriod,
    CompanyMetric,
    ReportSubmission,
    ProcessingLog,
    AuditLog,
    ReportingTemplate,
    SubmissionEvent,
)
from app.schemas import (
    LoginIn,
    TokenOut,
    UserOut,
    CompanyIn,
    CompanyOut,
    PeriodIn,
    PeriodOut,
    ChangePasswordIn,
    ReportingTemplateIn,
    TemplateVersionIn,
    CompanySubmitterIn,
    ReviewIn,
    DecisionIn,
)
from app.security import (
    verify_password,
    create_access_token,
    get_current_user,
    require_roles,
    hash_password,
)
from app.processing import ingest
from app.reporting_templates import create_template, get_template, list_templates
from app.lifecycle import approve_submission, mark_reviewed

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Business Portfolio Reporting & Intelligence Platform",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _template_payload(template: ReportingTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "version": template.version,
        "is_active": template.is_active,
        "metrics": [
            {
                "metric_key": metric.metric_key,
                "label": metric.label,
                "data_type": metric.data_type,
                "unit": metric.unit,
                "is_required": metric.is_required,
                "minimum_value": metric.minimum_value,
                "maximum_value": metric.maximum_value,
                "sort_order": metric.sort_order,
            }
            for metric in sorted(template.metrics, key=lambda item: item.sort_order)
        ],
    }


def _submission_for_user(
    submission_id: str, user: User, db: Session
) -> ReportSubmission:
    statement = select(ReportSubmission).where(
        ReportSubmission.id == submission_id,
        ReportSubmission.organization_id == user.organization_id,
    )
    if user.role == "company_submitter":
        statement = statement.where(
            or_(
                ReportSubmission.company_id == user.company_id,
                and_(
                    ReportSubmission.company_id.is_(None),
                    ReportSubmission.submitted_by == user.id,
                ),
            )
        )
    submission = db.scalar(statement)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status": "ready", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/api/v1/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        not user
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": create_access_token(user)}


@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/api/v1/auth/change-password")
def change_password(
    payload: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="password_changed",
            entity_type="user",
            entity_id=user.id,
        )
    )
    db.commit()
    return {"status": "password_changed"}


@app.get("/api/v1/organizations/me")
def organization_me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    org = db.get(Organization, user.organization_id)
    return {"id": org.id, "name": org.name, "slug": org.slug}


@app.get("/api/v1/companies", response_model=list[CompanyOut])
def list_companies(
    search: str | None = None,
    industry: str | None = None,
    status: str | None = "active",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Company).where(Company.organization_id == user.organization_id)
    if user.role == "company_submitter":
        stmt = stmt.where(Company.id == user.company_id)
    if search:
        stmt = stmt.where(Company.name.ilike(f"%{search}%"))
    if industry:
        stmt = stmt.where(Company.industry == industry)
    if status:
        stmt = stmt.where(Company.status == status)
    return db.scalars(stmt.order_by(Company.name).limit(limit).offset(offset)).all()


@app.post("/api/v1/companies", response_model=CompanyOut)
def create_company(
    payload: CompanyIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    slug = payload.identifier.lower()
    if db.scalar(
        select(Company).where(
            Company.organization_id == user.organization_id,
            Company.identifier == payload.identifier,
        )
    ):
        raise HTTPException(status_code=409, detail="Company identifier already exists")
    company = Company(
        organization_id=user.organization_id,
        identifier=payload.identifier,
        slug=slug,
        name=payload.name,
        industry=payload.industry,
        description=payload.description,
        website=payload.website,
    )
    db.add(company)
    db.flush()
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="company_created",
            entity_type="company",
            entity_id=company.id,
        )
    )
    db.commit()
    db.refresh(company)
    return company


@app.get("/api/v1/companies/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "company_submitter" and company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Company not found")
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.organization_id == user.organization_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.patch("/api/v1/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    payload: CompanyIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.organization_id == user.organization_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for k, v in payload.model_dump().items():
        setattr(company, k, v)
    db.commit()
    db.refresh(company)
    return company


@app.post("/api/v1/companies/{company_id}/submitters", status_code=201)
def create_company_submitter(
    company_id: str,
    payload: CompanySubmitterIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.organization_id == user.organization_id,
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if db.scalar(
        select(User).where(
            User.organization_id == user.organization_id,
            User.email == payload.email,
        )
    ):
        raise HTTPException(status_code=409, detail="User email already exists")
    company_user = User(
        organization_id=user.organization_id,
        company_id=company.id,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="company_submitter",
    )
    db.add(company_user)
    db.flush()
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="company_submitter_created",
            entity_type="user",
            entity_id=company_user.id,
            details_json={"company_id": company.id},
        )
    )
    db.commit()
    return {
        "id": company_user.id,
        "email": company_user.email,
        "role": company_user.role,
        "company_id": company_user.company_id,
    }


@app.post("/api/v1/reporting-templates", status_code=201)
def create_reporting_template(
    payload: ReportingTemplateIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(ReportingTemplate).where(
            ReportingTemplate.organization_id == user.organization_id,
            ReportingTemplate.name == payload.name,
            ReportingTemplate.version == 1,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Template name already exists")
    template = create_template(
        db,
        user.organization_id,
        user,
        payload.name,
        payload.description,
        [metric.model_dump() for metric in payload.metrics],
    )
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="reporting_template_created",
            entity_type="reporting_template",
            entity_id=template.id,
            details_json={"name": template.name, "version": template.version},
        )
    )
    db.commit()
    return _template_payload(template)


@app.get("/api/v1/reporting-templates")
def list_reporting_templates(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return [
        _template_payload(template)
        for template in list_templates(db, user.organization_id)
    ]


@app.post("/api/v1/reporting-templates/{template_id}/versions", status_code=201)
def create_reporting_template_version(
    template_id: str,
    payload: TemplateVersionIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    source = get_template(db, user.organization_id, template_id)
    if not source:
        raise HTTPException(status_code=404, detail="Reporting template not found")
    latest_version = db.scalar(
        select(func.max(ReportingTemplate.version)).where(
            ReportingTemplate.organization_id == user.organization_id,
            ReportingTemplate.name == source.name,
        )
    )
    db.query(ReportingTemplate).filter(
        ReportingTemplate.organization_id == user.organization_id,
        ReportingTemplate.name == source.name,
    ).update({"is_active": False}, synchronize_session=False)
    template = create_template(
        db,
        user.organization_id,
        user,
        source.name,
        payload.description if payload.description is not None else source.description,
        [metric.model_dump() for metric in payload.metrics],
        version=(latest_version or source.version) + 1,
    )
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="reporting_template_version_created",
            entity_type="reporting_template",
            entity_id=template.id,
            details_json={
                "source_template_id": source.id,
                "version": template.version,
            },
        )
    )
    db.commit()
    return _template_payload(template)


@app.delete("/api/v1/companies/{company_id}")
def deactivate_company(
    company_id: str,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.organization_id == user.organization_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.status = "inactive"
    db.commit()
    return {"status": "deactivated"}


@app.post("/api/v1/reporting-periods", response_model=PeriodOut)
def create_period(
    payload: PeriodIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    template_id = payload.template_id
    if template_id:
        template = get_template(db, user.organization_id, template_id)
        if not template or not template.is_active:
            raise HTTPException(
                status_code=404, detail="Active reporting template not found"
            )
    else:
        active_templates = [
            item
            for item in list_templates(db, user.organization_id)
            if item.is_active
        ]
        if len(active_templates) != 1:
            raise HTTPException(
                status_code=422,
                detail="Select a reporting template when zero or multiple templates are active",
            )
        template_id = active_templates[0].id
    existing = db.scalar(
        select(ReportingPeriod).where(
            ReportingPeriod.organization_id == user.organization_id,
            ReportingPeriod.year == payload.year,
            ReportingPeriod.month == payload.month,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Reporting period already exists")
    period = ReportingPeriod(
        organization_id=user.organization_id,
        template_id=template_id,
        year=payload.year,
        month=payload.month,
        start_date=date(payload.year, payload.month, 1),
        end_date=date(
            payload.year,
            payload.month,
            calendar.monthrange(payload.year, payload.month)[1],
        ),
    )
    db.add(period)
    db.flush()
    db.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="reporting_period_created",
            entity_type="reporting_period",
            entity_id=period.id,
            details_json={"year": period.year, "month": period.month, "template_id": template_id},
        )
    )
    db.commit()
    db.refresh(period)
    return period


@app.get("/api/v1/reporting-periods", response_model=list[PeriodOut])
def list_periods(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(ReportingPeriod)
        .where(ReportingPeriod.organization_id == user.organization_id)
        .order_by(ReportingPeriod.year.desc(), ReportingPeriod.month.desc())
    ).all()


@app.post("/api/v1/reports/upload")
async def upload_report(
    file: UploadFile = File(...),
    template_id: str | None = Form(default=None),
    resubmission_of_id: str | None = Form(default=None),
    user: User = Depends(require_roles("admin", "analyst", "company_submitter")),
    db: Session = Depends(get_db),
):
    data = await file.read(settings.max_upload_bytes + 1)
    try:
        submission, errors, idempotent_replay = ingest(
            data,
            file.filename or "upload.csv",
            user,
            db,
            settings.max_upload_bytes,
            template_id=template_id,
            resubmission_of_id=resubmission_of_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result = {
        "submission_id": submission.id,
        "status": submission.submission_status,
        "idempotent_replay": idempotent_replay,
        "total_rows": submission.total_rows,
        "valid_rows": submission.valid_rows,
        "invalid_rows": submission.invalid_rows,
        "duplicate_rows": submission.duplicate_rows,
        "errors": errors,
    }
    if submission.submission_status == "validation_failed":
        return JSONResponse(status_code=422, content=result)
    return result


@app.get("/api/v1/reports")
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    statement = select(ReportSubmission).where(
        ReportSubmission.organization_id == user.organization_id
    )
    if user.role == "company_submitter":
        statement = statement.where(
            or_(
                ReportSubmission.company_id == user.company_id,
                and_(
                    ReportSubmission.company_id.is_(None),
                    ReportSubmission.submitted_by == user.id,
                ),
            )
        )
    rows = db.scalars(
        statement.order_by(ReportSubmission.submitted_at.desc()).limit(100)
    ).all()
    return [
        {
            "id": r.id,
            "filename": r.original_filename,
            "status": r.submission_status,
            "valid_rows": r.valid_rows,
            "invalid_rows": r.invalid_rows,
            "submitted_at": r.submitted_at,
        }
        for r in rows
    ]


@app.get("/api/v1/reports/{submission_id}")
def get_report(
    submission_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = _submission_for_user(submission_id, user, db)
    return {
        "id": r.id,
        "filename": r.original_filename,
        "status": r.submission_status,
        "company_id": r.company_id,
        "reporting_period_id": r.reporting_period_id,
        "template_id": r.template_id,
        "reviewed_by": r.reviewed_by,
        "reviewed_at": r.reviewed_at,
        "decided_by": r.decided_by,
        "decided_at": r.decided_at,
        "decision_reason": r.decision_reason,
        "resubmission_of_id": r.resubmission_of_id,
        "total_rows": r.total_rows,
        "valid_rows": r.valid_rows,
        "invalid_rows": r.invalid_rows,
        "duplicate_rows": r.duplicate_rows,
        "error_summary": r.error_summary,
    }


@app.get("/api/v1/reports/{submission_id}/errors")
def report_errors(
    submission_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _submission_for_user(submission_id, user, db)
    log = db.scalar(
        select(ProcessingLog).where(
            ProcessingLog.submission_id == submission_id,
            ProcessingLog.organization_id == user.organization_id,
            ProcessingLog.event_type == "validation_errors",
        )
    )
    return log.details_json.get("errors", []) if log else []


@app.get("/api/v1/reports/{submission_id}/logs")
def report_logs(
    submission_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _submission_for_user(submission_id, user, db)
    return db.scalars(
        select(ProcessingLog).where(
            ProcessingLog.submission_id == submission_id,
            ProcessingLog.organization_id == user.organization_id,
        )
    ).all()


@app.get("/api/v1/reports/{submission_id}/events")
def report_events(
    submission_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission = _submission_for_user(submission_id, user, db)
    return db.scalars(
        select(SubmissionEvent)
        .where(
            SubmissionEvent.organization_id == user.organization_id,
            SubmissionEvent.submission_id == submission.id,
        )
        .order_by(SubmissionEvent.created_at, SubmissionEvent.id)
    ).all()


@app.post("/api/v1/reports/{submission_id}/review")
def review_report(
    submission_id: str,
    payload: ReviewIn,
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
):
    submission = _submission_for_user(submission_id, user, db)
    mark_reviewed(db, submission, user, payload.comment)
    db.commit()
    return {"id": submission.id, "status": submission.submission_status, "reviewed": True}


@app.post("/api/v1/reports/{submission_id}/decision")
def decide_report(
    submission_id: str,
    payload: DecisionIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    submission = _submission_for_user(submission_id, user, db)
    approve_submission(db, submission, user, payload.decision, payload.reason)
    db.commit()
    return {"id": submission.id, "status": submission.submission_status}


def _latest_metrics_by_company(user: User, db: Session):
    rows = db.execute(
        select(CompanyMetric, ReportingPeriod.year, ReportingPeriod.month)
        .join(
            ReportingPeriod,
            CompanyMetric.reporting_period_id == ReportingPeriod.id,
        )
        .join(ReportSubmission, CompanyMetric.report_submission_id == ReportSubmission.id)
        .where(CompanyMetric.organization_id == user.organization_id)
        .where(ReportSubmission.submission_status == "approved")
        .order_by(
            ReportingPeriod.year.desc(),
            ReportingPeriod.month.desc(),
            CompanyMetric.created_at.desc(),
            CompanyMetric.id,
        )
    ).all()
    latest = {}
    for metric, year, month in rows:
        latest.setdefault(metric.company_id, (metric, year, month))
    return list(latest.values())


def _sum_available(metrics: list[CompanyMetric], field: str):
    values = [getattr(metric, field) for metric in metrics]
    available = [value for value in values if value is not None]
    if not available:
        return None
    if field in {"revenue", "expenses", "cash_balance"}:
        return sum(available, Decimal("0"))
    return sum(available)


@app.get("/api/v1/analytics/portfolio/overview")
def portfolio_overview(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if user.role == "company_submitter":
        raise HTTPException(status_code=403, detail="Portfolio analytics are not available to company submitters")
    latest_reports = _latest_metrics_by_company(user, db)
    metrics = [metric for metric, _, _ in latest_reports]
    period_company_counts = {}
    for _, year, month in latest_reports:
        period_company_counts[(year, month)] = (
            period_company_counts.get((year, month), 0) + 1
        )
    companies = (
        db.scalar(
            select(func.count(Company.id)).where(
                Company.organization_id == user.organization_id,
                Company.status == "active",
            )
        )
        or 0
    )
    return {
        "active_companies": companies,
        "reporting_basis": "latest_available_report_per_company",
        "periods_may_differ": len(period_company_counts) > 1,
        "latest_reporting_periods": [
            {"year": year, "month": month, "company_count": count}
            for (year, month), count in sorted(period_company_counts.items())
        ],
        "total_revenue": (
            str(value) if (value := _sum_available(metrics, "revenue")) is not None else None
        ),
        "total_expenses": (
            str(value) if (value := _sum_available(metrics, "expenses")) is not None else None
        ),
        "total_profit": (
            str(
                sum(
                    (
                        metric.revenue - metric.expenses
                        for metric in metrics
                        if metric.revenue is not None and metric.expenses is not None
                    ),
                    Decimal("0"),
                )
            )
            if any(
                metric.revenue is not None and metric.expenses is not None
                for metric in metrics
            )
            else None
        ),
        "total_customers": _sum_available(metrics, "customer_count"),
        "total_employees": _sum_available(metrics, "employee_count"),
        "total_cash_balance": (
            str(value) if (value := _sum_available(metrics, "cash_balance")) is not None else None
        ),
        "metric_coverage": {
            field: sum(getattr(metric, field) is not None for metric in metrics)
            for field in (
                "revenue", "expenses", "new_customers",
                "customer_count", "employee_count", "cash_balance",
            )
        },
        "submitted_reports": db.scalar(
            select(func.count(ReportSubmission.id)).where(
                ReportSubmission.organization_id == user.organization_id
            )
        )
        or 0,
    }


@app.get("/api/v1/analytics/companies/{company_id}/overview")
def company_overview(
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.organization_id == user.organization_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if user.role == "company_submitter" and company.id != user.company_id:
        raise HTTPException(status_code=404, detail="Company not found")
    metrics = db.scalars(
        select(CompanyMetric)
        .join(
            ReportingPeriod,
            CompanyMetric.reporting_period_id == ReportingPeriod.id,
        )
        .join(ReportSubmission, CompanyMetric.report_submission_id == ReportSubmission.id)
        .where(
            CompanyMetric.organization_id == user.organization_id,
            CompanyMetric.company_id == company_id,
            ReportSubmission.submission_status == "approved",
        )
        .order_by(ReportingPeriod.year, ReportingPeriod.month)
    ).all()
    if not metrics:
        return {
            "company": company.name,
            "periods": 0,
            "revenue": None,
            "expenses": None,
            "profit": None,
            "new_customers": None,
            "latest_customers": None,
            "latest_employees": None,
            "latest_cash_balance": None,
            "latest_reporting_period": None,
        }
    latest = metrics[-1]
    latest_period = db.get(ReportingPeriod, latest.reporting_period_id)
    return {
        "company": company.name,
        "periods": len(metrics),
        "revenue": (
            str(value) if (value := _sum_available(metrics, "revenue")) is not None else None
        ),
        "expenses": (
            str(value) if (value := _sum_available(metrics, "expenses")) is not None else None
        ),
        "profit": (
            str(
                sum(
                    (
                        metric.revenue - metric.expenses
                        for metric in metrics
                        if metric.revenue is not None and metric.expenses is not None
                    ),
                    Decimal("0"),
                )
            )
            if any(
                metric.revenue is not None and metric.expenses is not None
                for metric in metrics
            )
            else None
        ),
        "new_customers": _sum_available(metrics, "new_customers"),
        "latest_customers": latest.customer_count,
        "latest_employees": latest.employee_count,
        "latest_cash_balance": (
            str(latest.cash_balance) if latest.cash_balance is not None else None
        ),
        "latest_reporting_period": {
            "year": latest_period.year,
            "month": latest_period.month,
        },
    }


@app.get("/api/v1/analytics/companies/{company_id}/trends")
def company_trends(
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == "company_submitter" and company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Company not found")
    company = db.scalar(
        select(Company).where(
            Company.id == company_id, Company.organization_id == user.organization_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    rows = db.scalars(
        select(CompanyMetric)
        .where(
            CompanyMetric.organization_id == user.organization_id,
            CompanyMetric.company_id == company_id,
        )
        .join(ReportingPeriod, CompanyMetric.reporting_period_id == ReportingPeriod.id)
        .join(ReportSubmission, CompanyMetric.report_submission_id == ReportSubmission.id)
        .where(ReportSubmission.submission_status == "approved")
        .order_by(ReportingPeriod.year, ReportingPeriod.month)
    ).all()
    return [
        {
            "period_id": m.reporting_period_id,
            "revenue": str(m.revenue) if m.revenue is not None else None,
            "expenses": str(m.expenses) if m.expenses is not None else None,
            "profit": (
                str(m.revenue - m.expenses)
                if m.revenue is not None and m.expenses is not None
                else None
            ),
            "customers": m.customer_count,
        }
        for m in rows
    ]


@app.get("/api/v1/audit-logs")
def audit_logs(
    user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    return db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == user.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()


@app.get("/api/v1/processing-logs")
def processing_logs(
    user: User = Depends(require_roles("admin", "analyst")),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(ProcessingLog)
        .where(ProcessingLog.organization_id == user.organization_id)
        .order_by(ProcessingLog.created_at.desc())
        .limit(100)
    ).all()
