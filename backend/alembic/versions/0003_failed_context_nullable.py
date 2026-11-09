from alembic import op
import sqlalchemy as sa

revision = "0003_failed_context_nullable"
down_revision = "0002_demo_email_example_domain"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "report_submissions",
        "company_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.alter_column(
        "report_submissions",
        "reporting_period_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade():
    connection = op.get_bind()
    incomplete_submissions = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM report_submissions
            WHERE company_id IS NULL OR reporting_period_id IS NULL
            """
        )
    ).scalar_one()
    if incomplete_submissions:
        raise RuntimeError(
            "Cannot restore required submission context while failed submissions exist."
        )

    op.alter_column(
        "report_submissions",
        "reporting_period_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    op.alter_column(
        "report_submissions",
        "company_id",
        existing_type=sa.String(length=36),
        nullable=False,
    )
