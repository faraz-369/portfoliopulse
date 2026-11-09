import csv
import hashlib
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.lifecycle import record_submission_event, transition_submission
from app.models import (
    AuditLog,
    Company,
    CompanyMetric,
    ProcessingLog,
    ReportSubmission,
    ReportingTemplate,
    ReportingPeriod,
    User,
)

IDENTITY_COLUMNS = ["company_identifier", "reporting_year", "reporting_month"]
METRIC_KEYS = [
    "revenue",
    "expenses",
    "customer_count",
    "new_customers",
    "employee_count",
    "cash_balance",
]
REQUIRED = IDENTITY_COLUMNS + METRIC_KEYS
DECIMAL_METRICS = {"revenue", "expenses", "cash_balance"}


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _row_count(data: bytes) -> int:
    try:
        rows = csv.reader(io.StringIO(data.decode("utf-8-sig")))
        return max(
            sum(1 for row in rows if row and any(cell.strip() for cell in row)) - 1,
            0,
        )
    except (UnicodeDecodeError, csv.Error):
        return 0


def _issue(row: int, column: str, value: str, rule: str, message: str) -> dict:
    return {
        "row": row,
        "column": column,
        "value": str(value)[:100],
        "rule": rule,
        "message": message,
    }


def parse_and_validate(
    data: bytes,
    org_id: str,
    db: Session,
    template: ReportingTemplate,
) -> tuple[list[dict], list[dict], list[dict]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [
            _issue(
                0,
                "file",
                "",
                "encoding",
                "CSV must be UTF-8 or UTF-8 with BOM",
            )
        ], []

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [_issue(0, "file", "", "empty", "CSV is empty")], []

    definitions = {metric.metric_key: metric for metric in template.metrics}
    expected_metrics = [key for key in METRIC_KEYS if key in definitions]
    required_metrics = {
        metric.metric_key for metric in template.metrics if metric.is_required
    }
    headers = reader.fieldnames
    supplied_metrics = headers[len(IDENTITY_COLUMNS) :]
    header_errors = []
    if headers[: len(IDENTITY_COLUMNS)] != IDENTITY_COLUMNS:
        header_errors.append(
            _issue(
                1,
                "header",
                ",".join(headers),
                "columns",
                "The first columns must be "
                + ", ".join(IDENTITY_COLUMNS),
            )
        )
    if len(headers) != len(set(headers)):
        header_errors.append(
            _issue(1, "header", ",".join(headers), "duplicate_column", "Column names must be unique")
        )
    if any(key not in expected_metrics for key in supplied_metrics):
        header_errors.append(
            _issue(
                1,
                "header",
                ",".join(headers),
                "unknown_column",
                "CSV includes metric columns not defined by the selected template",
            )
        )
    if [key for key in expected_metrics if key in supplied_metrics] != supplied_metrics:
        header_errors.append(
            _issue(
                1,
                "header",
                ",".join(headers),
                "column_order",
                "Metric columns must follow the selected template order",
            )
        )
    missing = required_metrics - set(supplied_metrics)
    if missing:
        header_errors.append(
            _issue(
                1,
                "header",
                ",".join(headers),
                "required_columns",
                f"Required template columns are missing: {', '.join(sorted(missing))}",
            )
        )
    if header_errors:
        return [], header_errors, []

    companies = {
        company.identifier: company
        for company in db.scalars(
            select(Company).where(Company.organization_id == org_id)
        ).all()
    }
    valid, errors, seen, resolved_contexts = [], [], set(), []
    for row_number, row in enumerate(reader, start=2):
        values = [value for value in row.values() if isinstance(value, str)]
        if not any(value.strip() for value in values) and None not in row:
            continue
        if None in row or any(value is None for value in row.values()):
            errors.append(
                _issue(
                    row_number,
                    "row",
                    "",
                    "structure",
                    "Row has a different number of values than the header",
                )
            )
            continue

        identity = tuple((row.get(key) or "").strip() for key in IDENTITY_COLUMNS)
        if identity in seen:
            errors.append(
                _issue(
                    row_number,
                    "row",
                    identity,
                    "duplicate_row",
                    "Duplicate company/reporting-period row",
                )
            )
            continue
        seen.add(identity)

        issues = []
        company_id = identity[0]
        company = companies.get(company_id)
        if not company:
            issues.append(
                (
                    "company_identifier",
                    company_id,
                    "company_exists",
                    "Company identifier is required and must be registered",
                )
            )

        try:
            year, month = int(identity[1]), int(identity[2])
            if year < 2000 or year > 2100 or not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            year, month = 0, 0
            issues.append(
                (
                    "reporting_month",
                    identity[2],
                    "valid_period",
                    "Reporting year/month is invalid",
                )
            )

        metric_values = {}
        for key in supplied_metrics:
            raw = (row.get(key) or "").strip()
            definition = definitions[key]
            if not raw:
                if definition.is_required:
                    issues.append(
                        (
                            key,
                            raw,
                            "required_metric",
                            f"{definition.label} is required by this template",
                        )
                    )
                else:
                    metric_values[key] = None
                continue
            try:
                if definition.data_type == "decimal":
                    value = Decimal(raw)
                    if not value.is_finite():
                        raise InvalidOperation
                    value = value.quantize(Decimal("0.01"))
                else:
                    if str(int(raw)) != raw:
                        raise ValueError
                    value = int(raw)
                numeric_value = Decimal(value)
                if (
                    definition.minimum_value is not None
                    and numeric_value < definition.minimum_value
                ):
                    raise ValueError("below_minimum")
                if (
                    definition.maximum_value is not None
                    and numeric_value > definition.maximum_value
                ):
                    raise ValueError("above_maximum")
                metric_values[key] = value
            except ValueError as exc:
                if str(exc) in {"below_minimum", "above_maximum"}:
                    message = (
                        f"Must be at least {definition.minimum_value}"
                        if str(exc) == "below_minimum"
                        else f"Must be at most {definition.maximum_value}"
                    )
                    rule = str(exc)
                else:
                    message = (
                        "Must be a valid decimal number"
                        if definition.data_type == "decimal"
                        else "Must be a whole number"
                    )
                    rule = "invalid_type"
                issues.append((key, raw, rule, message))
            except (InvalidOperation, ArithmeticError):
                issues.append((key, raw, "invalid_type", "Must be a valid number"))

        customers = metric_values.get("customer_count")
        new_customers = metric_values.get("new_customers")
        if (
            customers is not None
            and new_customers is not None
            and new_customers > customers
        ):
            issues.append(
                (
                    "new_customers",
                    str(new_customers),
                    "new_le_total",
                    "New customers cannot exceed total customers",
                )
            )

        period = None
        if company and year and month:
            period = db.scalar(
                select(ReportingPeriod).where(
                    ReportingPeriod.organization_id == org_id,
                    ReportingPeriod.year == year,
                    ReportingPeriod.month == month,
                )
            )
            if not period:
                issues.append(
                    (
                        "reporting_month",
                        str(month),
                        "period_registered",
                        "Reporting period has not been registered",
                    )
                )
            elif period.template_id != template.id:
                issues.append(
                    (
                        "reporting_month",
                        str(month),
                        "template_period_mismatch",
                        "Selected template does not match the reporting period",
                    )
                )
            else:
                resolved_contexts.append(
                    {"row": row_number, "company": company, "period": period}
                )

        if issues:
            errors.extend(
                _issue(row_number, column, value, rule, message)
                for column, value, rule, message in issues
            )
        else:
            valid.append(
                {
                    "row": row_number,
                    "company": company,
                    "period": period,
                    "metrics": metric_values,
                }
            )
    return valid, errors, resolved_contexts


def _validation_errors(db: Session, submission_id: str) -> list[dict]:
    log = db.scalar(
        select(ProcessingLog).where(
            ProcessingLog.submission_id == submission_id,
            ProcessingLog.event_type == "validation_errors",
        )
    )
    return log.details_json.get("errors", []) if log else []


def ingest(
    data: bytes,
    filename: str,
    user: User,
    db: Session,
    max_bytes: int,
    template_id: str | None = None,
    resubmission_of_id: str | None = None,
) -> tuple[ReportSubmission, list[dict], bool]:
    if len(data) > max_bytes:
        raise ValueError("Upload exceeds configured maximum size")
    if not filename.lower().endswith(".csv"):
        raise ValueError("Only .csv files are accepted")

    digest = checksum(data)
    existing = db.scalar(
        select(ReportSubmission).where(
            ReportSubmission.organization_id == user.organization_id,
            ReportSubmission.file_checksum == digest,
        )
    )
    if existing:
        if (
            user.role == "company_submitter"
            and existing.company_id != user.company_id
            and existing.submitted_by != user.id
        ):
            raise ValueError("This file checksum is already associated with another submission")
        return existing, _validation_errors(db, existing.id), True

    if template_id:
        template = db.scalar(
            select(ReportingTemplate)
            .options(selectinload(ReportingTemplate.metrics))
            .where(
                ReportingTemplate.id == template_id,
                ReportingTemplate.organization_id == user.organization_id,
            )
        )
    else:
        active_templates = db.scalars(
            select(ReportingTemplate)
            .options(selectinload(ReportingTemplate.metrics))
            .where(
                ReportingTemplate.organization_id == user.organization_id,
                ReportingTemplate.is_active.is_(True),
            )
            .order_by(ReportingTemplate.version.desc())
        ).all()
        if len(active_templates) > 1:
            raise ValueError("Select a reporting template for this upload")
        template = active_templates[0] if active_templates else None
    if template is None:
        raise ValueError("A reporting template is required before uploading")

    parent = None
    if resubmission_of_id:
        parent = db.scalar(
            select(ReportSubmission).where(
                ReportSubmission.id == resubmission_of_id,
                ReportSubmission.organization_id == user.organization_id,
            )
        )
        if not parent:
            raise ValueError("Resubmission source not found in this organisation")
        if parent.submission_status not in {
            "validation_failed",
            "rejected",
            "approved",
            "superseded",
        }:
            raise ValueError("Submission is not eligible for a corrected resubmission")

    submission = ReportSubmission(
        organization_id=user.organization_id,
        template_id=template.id,
        original_filename=filename[:255],
        file_checksum=digest,
        file_size=len(data),
        submission_status="submitted",
        submitted_by=user.id,
        resubmission_of_id=parent.id if parent else None,
        total_rows=_row_count(data),
    )
    try:
        db.add(submission)
        db.flush()
        record_submission_event(db, submission, user, None, "submitted")
        transition_submission(db, submission, user, "processing")
        valid, errors, resolved_contexts = parse_and_validate(
            data, user.organization_id, db, template
        )
        if user.role == "company_submitter":
            company_mismatch = [
                row
                for row in resolved_contexts
                if row["company"].id != user.company_id
            ]
            if company_mismatch:
                errors.extend(
                    _issue(
                        row["row"],
                        "company_identifier",
                        row["company"].identifier,
                        "company_access",
                        "Company submitters may upload reports only for their own company",
                    )
                    for row in company_mismatch
                )
                mismatch_rows = {row["row"] for row in company_mismatch}
                valid = [row for row in valid if row["row"] not in mismatch_rows]
                resolved_contexts = [
                    row
                    for row in resolved_contexts
                    if row["row"] not in mismatch_rows
                ]

        contexts = {
            (row["company"].id, row["period"].id) for row in resolved_contexts
        }
        if len(contexts) > 1:
            errors.append(
                _issue(
                    0,
                    "file",
                    "",
                    "single_company_period",
                    "A submission must contain one company and one reporting period",
                )
            )
            valid = []
            resolved_contexts = []
            contexts = set()

        if parent and contexts:
            company_id, period_id = next(iter(contexts))
            if (
                parent.company_id is not None
                and parent.company_id != company_id
            ) or (
                parent.reporting_period_id is not None
                and parent.reporting_period_id != period_id
            ):
                errors.append(
                    _issue(
                        0,
                        "file",
                        "",
                        "resubmission_context",
                        "A corrected submission must use the original company and period",
                    )
                )
                valid = []
                resolved_contexts = []
                contexts = set()

        if len(contexts) == 1:
            company_id, period_id = next(iter(contexts))
            submission.company_id = company_id
            submission.reporting_period_id = period_id
            db.flush()
        for row in valid:
            values = row["metrics"]
            db.add(
                CompanyMetric(
                    organization_id=user.organization_id,
                    company_id=row["company"].id,
                    reporting_period_id=row["period"].id,
                    report_submission_id=submission.id,
                    revenue=values.get("revenue"),
                    expenses=values.get("expenses"),
                    customer_count=values.get("customer_count"),
                    new_customers=values.get("new_customers"),
                    employee_count=values.get("employee_count"),
                    cash_balance=values.get("cash_balance"),
                )
            )

        submission.valid_rows = len(valid)
        submission.invalid_rows = len(
            {error["row"] for error in errors if error.get("row", 0) > 1}
        )
        if errors and not submission.invalid_rows:
            submission.invalid_rows = max(submission.total_rows, 1)
        submission.duplicate_rows = sum(
            error["rule"] in {"duplicate_row", "period_already_reported"}
            for error in errors
        )
        submission.processed_at = datetime.now(timezone.utc)
        submission.error_summary = (
            f"{len(errors)} validation issue(s)" if errors else None
        )
        final_state = "validation_failed" if errors else "pending_review"
        transition_submission(
            db,
            submission,
            user,
            final_state,
            "Validation errors recorded" if errors else "Validation passed",
        )
        db.add(
            ProcessingLog(
                organization_id=user.organization_id,
                submission_id=submission.id,
                event_type="ingestion_failed" if errors else "ingestion_completed",
                severity="error" if errors else "info",
                message=(
                    "CSV validation failed; accepted rows remain unapproved"
                    if errors
                    else "CSV processing completed and is awaiting review"
                ),
                details_json={
                    "accepted": len(valid),
                    "errors": len(errors),
                    "total_rows": submission.total_rows,
                },
            )
        )
        db.add(
            ProcessingLog(
                organization_id=user.organization_id,
                submission_id=submission.id,
                event_type="validation_errors",
                severity="warning" if errors else "info",
                message="Validation results recorded",
                details_json={"errors": errors},
            )
        )
        db.add(
            AuditLog(
                organization_id=user.organization_id,
                user_id=user.id,
                action="report_submitted",
                entity_type="report_submission",
                entity_id=submission.id,
                details_json={
                    "template_id": template.id,
                    "resubmission_of_id": submission.resubmission_of_id,
                    "filename": submission.original_filename,
                },
            )
        )
        db.commit()
        db.refresh(submission)
        return submission, errors, False
    except Exception:
        db.rollback()
        raise
