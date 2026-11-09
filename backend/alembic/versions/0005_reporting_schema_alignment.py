from alembic import op
import sqlalchemy as sa

revision = "0005_reporting_schema_alignment"
down_revision = "0004_reporting_lifecycle"
branch_labels = None
depends_on = None


LEGACY_FOREIGN_KEYS = (
    ("audit_logs", "audit_logs_user_id_fkey"),
    ("company_metrics", "company_metrics_company_id_fkey"),
    ("company_metrics", "company_metrics_report_submission_id_fkey"),
    ("company_metrics", "company_metrics_reporting_period_id_fkey"),
    ("processing_logs", "processing_logs_submission_id_fkey"),
    ("report_submissions", "report_submissions_reporting_period_id_fkey"),
    ("report_submissions", "report_submissions_company_id_fkey"),
    ("report_submissions", "report_submissions_submitted_by_fkey"),
)


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for table_name, constraint_name in LEGACY_FOREIGN_KEYS:
        if any(
            item["name"] == constraint_name
            for item in inspector.get_foreign_keys(table_name)
        ):
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")

    role_column = next(
        column for column in inspector.get_columns("users") if column["name"] == "role"
    )
    role_length = getattr(role_column["type"], "length", None)
    if role_length == 20:
        op.alter_column(
            "users",
            "role",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
    elif role_length != 30:
        raise RuntimeError(f"Unexpected users.role column length: {role_length}")

    indexes = {
        item["name"] for item in inspector.get_indexes("submission_events")
    }
    if "ix_submission_events_organization_id" not in indexes:
        op.create_index(
            "ix_submission_events_organization_id",
            "submission_events",
            ["organization_id"],
        )
    if "ix_submission_events_submission_id" not in indexes:
        op.create_index(
            "ix_submission_events_submission_id",
            "submission_events",
            ["submission_id"],
        )


def downgrade():
    op.drop_index(
        "ix_submission_events_submission_id", table_name="submission_events"
    )
    op.drop_index(
        "ix_submission_events_organization_id", table_name="submission_events"
    )
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

    op.create_foreign_key(
        "audit_logs_user_id_fkey", "audit_logs", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "company_metrics_company_id_fkey",
        "company_metrics",
        "companies",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "company_metrics_report_submission_id_fkey",
        "company_metrics",
        "report_submissions",
        ["report_submission_id"],
        ["id"],
    )
    op.create_foreign_key(
        "company_metrics_reporting_period_id_fkey",
        "company_metrics",
        "reporting_periods",
        ["reporting_period_id"],
        ["id"],
    )
    op.create_foreign_key(
        "processing_logs_submission_id_fkey",
        "processing_logs",
        "report_submissions",
        ["submission_id"],
        ["id"],
    )
    op.create_foreign_key(
        "report_submissions_reporting_period_id_fkey",
        "report_submissions",
        "reporting_periods",
        ["reporting_period_id"],
        ["id"],
    )
    op.create_foreign_key(
        "report_submissions_company_id_fkey",
        "report_submissions",
        "companies",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "report_submissions_submitted_by_fkey",
        "report_submissions",
        "users",
        ["submitted_by"],
        ["id"],
    )
