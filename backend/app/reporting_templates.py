from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Organization, ReportingTemplate, TemplateMetric, User

DEFAULT_METRICS = [
    ("revenue", "Revenue", "decimal", "currency"),
    ("expenses", "Expenses", "decimal", "currency"),
    ("customer_count", "Customers", "integer", "people"),
    ("new_customers", "New customers", "integer", "people"),
    ("employee_count", "Employees", "integer", "people"),
    ("cash_balance", "Cash balance", "decimal", "currency"),
]


def ensure_default_template(db: Session, organization: Organization) -> ReportingTemplate:
    template = db.scalar(
        select(ReportingTemplate).where(
            ReportingTemplate.organization_id == organization.id,
            ReportingTemplate.name == "Standard Monthly Metrics",
            ReportingTemplate.version == 1,
        )
    )
    if template:
        return template
    admin = db.scalar(
        select(User).where(
            User.organization_id == organization.id,
            User.role == "admin",
            User.is_active.is_(True),
        )
    )
    if not admin:
        raise RuntimeError(
            "Cannot create the default reporting template without an active organisation admin."
        )
    return create_template(
        db,
        organization.id,
        admin,
        "Standard Monthly Metrics",
        "Default synthetic monthly performance reporting template.",
        [
            {
                "metric_key": key,
                "label": label,
                "data_type": data_type,
                "unit": unit,
                "is_required": True,
                "minimum_value": 0,
                "maximum_value": None,
                "sort_order": position,
            }
            for position, (key, label, data_type, unit) in enumerate(DEFAULT_METRICS)
        ],
    )


def create_template(
    db: Session,
    organization_id: str,
    actor: User,
    name: str,
    description: str | None,
    metrics: list[dict],
    version: int = 1,
) -> ReportingTemplate:
    template = ReportingTemplate(
        organization_id=organization_id,
        name=name,
        description=description,
        version=version,
        is_active=True,
        created_by=actor.id,
    )
    template.metrics = [
        TemplateMetric(
            organization_id=organization_id,
            metric_key=metric["metric_key"],
            label=metric["label"],
            data_type=metric["data_type"],
            unit=metric["unit"],
            is_required=metric["is_required"],
            minimum_value=metric["minimum_value"],
            maximum_value=metric["maximum_value"],
            sort_order=metric["sort_order"],
        )
        for metric in metrics
    ]
    db.add(template)
    db.flush()
    return template


def get_template(
    db: Session, organization_id: str, template_id: str
) -> ReportingTemplate | None:
    return db.scalar(
        select(ReportingTemplate)
        .options(selectinload(ReportingTemplate.metrics))
        .where(
            ReportingTemplate.organization_id == organization_id,
            ReportingTemplate.id == template_id,
        )
    )


def list_templates(db: Session, organization_id: str) -> list[ReportingTemplate]:
    return list(
        db.scalars(
            select(ReportingTemplate)
            .options(selectinload(ReportingTemplate.metrics))
            .where(ReportingTemplate.organization_id == organization_id)
            .order_by(
                ReportingTemplate.name,
                ReportingTemplate.version.desc(),
            )
        ).all()
    )
