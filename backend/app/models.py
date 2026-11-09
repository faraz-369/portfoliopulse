import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
        UniqueConstraint("organization_id", "id", name="uq_user_org_id"),
        CheckConstraint(
            "role IN ('admin', 'analyst', 'viewer', 'company_submitter')",
            name="ck_user_known_role",
        ),
        CheckConstraint(
            "(role = 'company_submitter' AND company_id IS NOT NULL) OR "
            "(role <> 'company_submitter' AND company_id IS NULL)",
            name="ck_user_company_role_binding",
        ),
        ForeignKeyConstraint(
            ["organization_id", "company_id"],
            ["companies.organization_id", "companies.id"],
            name="fk_user_company_same_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    organization = relationship("Organization", back_populates="users")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_company_org_slug"),
        UniqueConstraint("organization_id", "id", name="uq_company_org_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    identifier: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(100))
    industry: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReportingTemplate(Base):
    __tablename__ = "reporting_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", "version", name="uq_template_org_name_version"
        ),
        UniqueConstraint("organization_id", "id", name="uq_template_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "created_by"],
            ["users.organization_id", "users.id"],
            name="fk_template_creator_same_org",
        ),
        CheckConstraint("version >= 1", name="ck_template_positive_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    metrics = relationship(
        "TemplateMetric", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateMetric(Base):
    __tablename__ = "template_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "template_id",
            "metric_key",
            name="uq_template_metric_key",
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["reporting_templates.organization_id", "reporting_templates.id"],
            name="fk_template_metric_same_org",
        ),
        CheckConstraint(
            "data_type IN ('decimal', 'integer')", name="ck_metric_definition_type"
        ),
        CheckConstraint(
            "minimum_value IS NULL OR maximum_value IS NULL OR "
            "minimum_value <= maximum_value",
            name="ck_metric_definition_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    template_id: Mapped[str] = mapped_column(String(36), index=True)
    metric_key: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(120))
    data_type: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str] = mapped_column(String(40))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    maximum_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template = relationship("ReportingTemplate", back_populates="metrics")


class ReportingPeriod(Base):
    __tablename__ = "reporting_periods"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "year", "month", name="uq_period_org_year_month"
        ),
        UniqueConstraint("organization_id", "id", name="uq_period_org_id"),
        UniqueConstraint(
            "organization_id", "id", "template_id", name="uq_period_template_scope"
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["reporting_templates.organization_id", "reporting_templates.id"],
            name="fk_period_template_same_org",
        ),
        CheckConstraint("start_date <= end_date", name="ck_period_dates_ordered"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    template_id: Mapped[str] = mapped_column(String(36), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")


class ReportSubmission(Base):
    __tablename__ = "report_submissions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "file_checksum", name="uq_submission_org_checksum"
        ),
        UniqueConstraint("organization_id", "id", name="uq_submission_org_id"),
        UniqueConstraint(
            "organization_id",
            "id",
            "company_id",
            "reporting_period_id",
            name="uq_submission_metric_scope",
        ),
        ForeignKeyConstraint(
            ["organization_id", "company_id"],
            ["companies.organization_id", "companies.id"],
            name="fk_submission_company_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "reporting_period_id", "template_id"],
            [
                "reporting_periods.organization_id",
                "reporting_periods.id",
                "reporting_periods.template_id",
            ],
            name="fk_submission_period_template_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["reporting_templates.organization_id", "reporting_templates.id"],
            name="fk_submission_template_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "submitted_by"],
            ["users.organization_id", "users.id"],
            name="fk_submission_submitter_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "reviewed_by"],
            ["users.organization_id", "users.id"],
            name="fk_submission_reviewer_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "decided_by"],
            ["users.organization_id", "users.id"],
            name="fk_submission_decider_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "resubmission_of_id"],
            ["report_submissions.organization_id", "report_submissions.id"],
            name="fk_submission_resubmission_same_org",
        ),
        CheckConstraint(
            "(company_id IS NULL AND reporting_period_id IS NULL) OR "
            "(company_id IS NOT NULL AND reporting_period_id IS NOT NULL)",
            name="ck_submission_context_complete",
        ),
        CheckConstraint(
            "submission_status IN ('submitted', 'processing', 'validation_failed', "
            "'pending_review', 'approved', 'rejected', 'superseded')",
            name="ck_submission_valid_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    reporting_period_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    template_id: Mapped[str] = mapped_column(String(36), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_checksum: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer)
    submission_status: Mapped[str] = mapped_column(String(30), default="submitted")
    submitted_by: Mapped[str] = mapped_column(String(36))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    resubmission_of_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


Index(
    "uq_approved_submission_company_period",
    ReportSubmission.organization_id,
    ReportSubmission.company_id,
    ReportSubmission.reporting_period_id,
    unique=True,
    postgresql_where=(ReportSubmission.submission_status == "approved"),
    sqlite_where=(ReportSubmission.submission_status == "approved"),
)


class CompanyMetric(Base):
    __tablename__ = "company_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "report_submission_id",
            "company_id",
            "reporting_period_id",
            name="uq_metric_submission_company_period",
        ),
        ForeignKeyConstraint(
            ["organization_id", "company_id"],
            ["companies.organization_id", "companies.id"],
            name="fk_metric_company_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "report_submission_id", "company_id", "reporting_period_id"],
            [
                "report_submissions.organization_id",
                "report_submissions.id",
                "report_submissions.company_id",
                "report_submissions.reporting_period_id",
            ],
            name="fk_metric_submission_context",
        ),
        ForeignKeyConstraint(
            ["organization_id", "reporting_period_id"],
            ["reporting_periods.organization_id", "reporting_periods.id"],
            name="fk_metric_period_same_org",
        ),
        CheckConstraint(
            "revenue IS NULL OR revenue >= 0",
            name="ck_metric_nonnegative_revenue",
        ),
        CheckConstraint(
            "expenses IS NULL OR expenses >= 0",
            name="ck_metric_nonnegative_expenses",
        ),
        CheckConstraint(
            "cash_balance IS NULL OR cash_balance >= 0",
            name="ck_metric_nonnegative_cash",
        ),
        CheckConstraint(
            "customer_count IS NULL OR customer_count >= 0",
            name="ck_metric_nonnegative_customers",
        ),
        CheckConstraint(
            "new_customers IS NULL OR new_customers >= 0",
            name="ck_metric_nonnegative_new_customers",
        ),
        CheckConstraint(
            "employee_count IS NULL OR employee_count >= 0",
            name="ck_metric_nonnegative_employees",
        ),
        CheckConstraint(
            "new_customers IS NULL OR customer_count IS NULL OR "
            "new_customers <= customer_count",
            name="ck_metric_new_customers_bounded",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    company_id: Mapped[str] = mapped_column(String(36), index=True)
    reporting_period_id: Mapped[str] = mapped_column(String(36), index=True)
    report_submission_id: Mapped[str] = mapped_column(String(36), index=True)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expenses: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    customer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_customers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cash_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SubmissionEvent(Base):
    __tablename__ = "submission_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "submission_id"],
            ["report_submissions.organization_id", "report_submissions.id"],
            name="fk_submission_event_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_id"],
            ["users.organization_id", "users.id"],
            name="fk_submission_event_actor_same_org",
        ),
        Index("ix_submission_events_timeline", "organization_id", "submission_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    submission_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str] = mapped_column(String(36))
    previous_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_state: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "submission_id"],
            ["report_submissions.organization_id", "report_submissions.id"],
            name="fk_processing_log_same_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    submission_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), default="info")
    message: Mapped[str] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_audit_user_same_org",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
