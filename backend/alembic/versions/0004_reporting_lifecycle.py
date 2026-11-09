import uuid

from alembic import op
import sqlalchemy as sa

revision = "0004_reporting_lifecycle"
down_revision = "0003_failed_context_nullable"
branch_labels = None
depends_on = None

METRICS = (
    ("revenue", "Revenue", "decimal", "currency", True),
    ("expenses", "Expenses", "decimal", "currency", True),
    ("customer_count", "Customers", "integer", "people", True),
    ("new_customers", "New customers", "integer", "people", True),
    ("employee_count", "Employees", "integer", "people", True),
    ("cash_balance", "Cash balance", "decimal", "currency", True),
)


def _assert_existing_relationships_are_consistent(connection):
    checks = {
        "submission company/period/user context": """
            SELECT COUNT(*)
            FROM report_submissions s
            LEFT JOIN companies c
              ON c.id = s.company_id AND c.organization_id = s.organization_id
            LEFT JOIN reporting_periods p
              ON p.id = s.reporting_period_id AND p.organization_id = s.organization_id
            JOIN users u ON u.id = s.submitted_by
            WHERE (s.company_id IS NOT NULL AND c.id IS NULL)
               OR (s.reporting_period_id IS NOT NULL AND p.id IS NULL)
               OR u.organization_id <> s.organization_id
               OR (s.company_id IS NOT NULL AND s.reporting_period_id IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1 FROM company_metrics m
                       WHERE m.organization_id = s.organization_id
                         AND m.company_id = s.company_id
                         AND m.reporting_period_id = s.reporting_period_id
                   )
                   AND c.id IS NULL)
        """,
        "submission submitter tenant context": """
            SELECT COUNT(*)
            FROM report_submissions s
            LEFT JOIN users u
              ON u.id = s.submitted_by AND u.organization_id = s.organization_id
            WHERE u.id IS NULL
        """,
        "metric company/period/submission context": """
            SELECT COUNT(*)
            FROM company_metrics m
            LEFT JOIN companies c
              ON c.id = m.company_id AND c.organization_id = m.organization_id
            LEFT JOIN reporting_periods p
              ON p.id = m.reporting_period_id AND p.organization_id = m.organization_id
            LEFT JOIN report_submissions s
              ON s.id = m.report_submission_id
             AND s.organization_id = m.organization_id
             AND s.company_id = m.company_id
             AND s.reporting_period_id = m.reporting_period_id
            WHERE c.id IS NULL OR p.id IS NULL OR s.id IS NULL
        """,
        "processing log tenant context": """
            SELECT COUNT(*)
            FROM processing_logs l
            LEFT JOIN report_submissions s
              ON s.id = l.submission_id AND s.organization_id = l.organization_id
            WHERE s.id IS NULL
        """,
        "audit actor tenant context": """
            SELECT COUNT(*)
            FROM audit_logs a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE a.user_id IS NOT NULL
              AND (u.id IS NULL OR u.organization_id <> a.organization_id)
        """,
        "submission context pair": """
            SELECT COUNT(*)
            FROM report_submissions
            WHERE (company_id IS NULL) <> (reporting_period_id IS NULL)
        """,
        "submission roles": """
            SELECT COUNT(*) FROM users
            WHERE role NOT IN ('admin', 'analyst', 'viewer')
        """,
        "metric count relationship": """
            SELECT COUNT(*) FROM company_metrics
            WHERE new_customers > customer_count
        """,
        "reporting period dates": """
            SELECT COUNT(*) FROM reporting_periods WHERE start_date > end_date
        """,
    }
    for label, statement in checks.items():
        count = connection.execute(sa.text(statement)).scalar_one()
        if count:
            raise RuntimeError(
                f"Migration stopped: {count} existing {label} record(s) "
                "violate tenant integrity. Resolve those records before retrying."
            )


def _create_reporting_tables():
    op.create_table(
        "reporting_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by"],
            ["users.organization_id", "users.id"],
            name="fk_template_creator_same_org",
        ),
        sa.UniqueConstraint(
            "organization_id", "name", "version", name="uq_template_org_name_version"
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_template_org_id"),
        sa.CheckConstraint("version >= 1", name="ck_template_positive_version"),
    )
    op.create_index(
        "ix_reporting_templates_organization_id",
        "reporting_templates",
        ["organization_id"],
    )

    op.create_table(
        "template_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("metric_key", sa.String(50), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("data_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("minimum_value", sa.Numeric(18, 2)),
        sa.Column("maximum_value", sa.Numeric(18, 2)),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["reporting_templates.organization_id", "reporting_templates.id"],
            name="fk_template_metric_same_org",
        ),
        sa.UniqueConstraint(
            "organization_id", "template_id", "metric_key", name="uq_template_metric_key"
        ),
        sa.CheckConstraint(
            "data_type IN ('decimal', 'integer')", name="ck_metric_definition_type"
        ),
        sa.CheckConstraint(
            "minimum_value IS NULL OR maximum_value IS NULL OR "
            "minimum_value <= maximum_value",
            name="ck_metric_definition_range",
        ),
    )
    op.create_index(
        "ix_template_metrics_organization_id", "template_metrics", ["organization_id"]
    )
    op.create_index("ix_template_metrics_template_id", "template_metrics", ["template_id"])

    op.create_table(
        "submission_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("submission_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("previous_state", sa.String(30)),
        sa.Column("new_state", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "submission_id"],
            ["report_submissions.organization_id", "report_submissions.id"],
            name="fk_submission_event_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_id"],
            ["users.organization_id", "users.id"],
            name="fk_submission_event_actor_same_org",
        ),
    )
    op.create_index(
        "ix_submission_events_timeline",
        "submission_events",
        ["organization_id", "submission_id", "created_at"],
    )


def upgrade():
    connection = op.get_bind()
    existing_tables = set(sa.inspect(connection).get_table_names())
    if "reporting_templates" in existing_tables:
        expected_tables = {
            "reporting_templates",
            "template_metrics",
            "submission_events",
        }
        missing_tables = expected_tables - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Migration stopped: a partial reporting lifecycle schema already "
                f"exists; missing tables: {', '.join(sorted(missing_tables))}."
            )
        return

    _assert_existing_relationships_are_consistent(connection)
    op.create_unique_constraint(
        "uq_user_org_id", "users", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_company_org_id", "companies", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_period_org_id", "reporting_periods", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_submission_org_id", "report_submissions", ["organization_id", "id"]
    )
    _create_reporting_tables()

    op.add_column(
        "users", sa.Column("company_id", sa.String(36), nullable=True)
    )
    op.add_column(
        "reporting_periods", sa.Column("template_id", sa.String(36), nullable=True)
    )
    op.add_column(
        "report_submissions", sa.Column("template_id", sa.String(36), nullable=True)
    )
    op.add_column(
        "report_submissions", sa.Column("reviewed_by", sa.String(36), nullable=True)
    )
    op.add_column(
        "report_submissions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "report_submissions", sa.Column("decided_by", sa.String(36), nullable=True)
    )
    op.add_column(
        "report_submissions",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "report_submissions", sa.Column("decision_reason", sa.Text(), nullable=True)
    )
    op.add_column(
        "report_submissions",
        sa.Column("resubmission_of_id", sa.String(36), nullable=True),
    )

    organizations = connection.execute(
        sa.text("SELECT id FROM organizations ORDER BY id")
    ).scalars()
    defaults = {}
    for organization_id in organizations:
        template_id = str(uuid.uuid4())
        defaults[organization_id] = template_id
        connection.execute(
            sa.text(
                """
                INSERT INTO reporting_templates
                    (id, organization_id, name, description, version, is_active, created_by, created_at)
                VALUES
                    (:id, :organization_id, 'Standard Monthly Metrics',
                     'Migrated default template; all legacy metrics are required.',
                     1, TRUE, NULL, CURRENT_TIMESTAMP)
                """
            ),
            {"id": template_id, "organization_id": organization_id},
        )
        for sort_order, (metric_key, label, data_type, unit, required) in enumerate(
            METRICS
        ):
            connection.execute(
                sa.text(
                    """
                    INSERT INTO template_metrics
                        (id, organization_id, template_id, metric_key, label,
                         data_type, unit, is_required, minimum_value, maximum_value, sort_order)
                    VALUES
                        (:id, :organization_id, :template_id, :metric_key, :label,
                         :data_type, :unit, :is_required, 0, NULL, :sort_order)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "organization_id": organization_id,
                    "template_id": template_id,
                    "metric_key": metric_key,
                    "label": label,
                    "data_type": data_type,
                    "unit": unit,
                    "is_required": required,
                    "sort_order": sort_order,
                },
            )

    for organization_id, template_id in defaults.items():
        connection.execute(
            sa.text(
                "UPDATE reporting_periods SET template_id = :template_id "
                "WHERE organization_id = :organization_id"
            ),
            {"template_id": template_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                """
                UPDATE report_submissions
                SET template_id = COALESCE(
                    (SELECT p.template_id FROM reporting_periods p
                     WHERE p.id = report_submissions.reporting_period_id
                       AND p.organization_id = report_submissions.organization_id),
                    :template_id
                )
                WHERE organization_id = :organization_id
                """
            ),
            {"template_id": template_id, "organization_id": organization_id},
        )

    connection.execute(
        sa.text(
            """
            UPDATE report_submissions
            SET submission_status = CASE
                WHEN EXISTS (
                    SELECT 1 FROM company_metrics m
                    WHERE m.report_submission_id = report_submissions.id
                ) THEN 'approved'
                ELSE 'validation_failed'
            END
            """
        )
    )

    for column in (
        "revenue",
        "expenses",
        "customer_count",
        "new_customers",
        "employee_count",
        "cash_balance",
    ):
        op.alter_column(
            "company_metrics",
            column,
            existing_type=(
                sa.Numeric(18, 2)
                if column in {"revenue", "expenses", "cash_balance"}
                else sa.Integer()
            ),
            nullable=True,
        )

    op.drop_constraint("uq_metric_company_period", "company_metrics", type_="unique")
    op.create_unique_constraint(
        "uq_metric_submission_company_period",
        "company_metrics",
        ["organization_id", "report_submission_id", "company_id", "reporting_period_id"],
    )
    op.create_unique_constraint(
        "uq_period_template_scope",
        "reporting_periods",
        ["organization_id", "id", "template_id"],
    )
    op.create_unique_constraint(
        "uq_submission_metric_scope",
        "report_submissions",
        ["organization_id", "id", "company_id", "reporting_period_id"],
    )
    op.create_foreign_key(
        "fk_user_company_same_org",
        "users",
        "companies",
        ["organization_id", "company_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_period_template_same_org",
        "reporting_periods",
        "reporting_templates",
        ["organization_id", "template_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_company_same_org",
        "report_submissions",
        "companies",
        ["organization_id", "company_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_period_template_same_org",
        "report_submissions",
        "reporting_periods",
        ["organization_id", "reporting_period_id", "template_id"],
        ["organization_id", "id", "template_id"],
    )
    op.create_foreign_key(
        "fk_submission_template_same_org",
        "report_submissions",
        "reporting_templates",
        ["organization_id", "template_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_submitter_same_org",
        "report_submissions",
        "users",
        ["organization_id", "submitted_by"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_reviewer_same_org",
        "report_submissions",
        "users",
        ["organization_id", "reviewed_by"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_decider_same_org",
        "report_submissions",
        "users",
        ["organization_id", "decided_by"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_submission_resubmission_same_org",
        "report_submissions",
        "report_submissions",
        ["organization_id", "resubmission_of_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_metric_company_same_org",
        "company_metrics",
        "companies",
        ["organization_id", "company_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_metric_submission_context",
        "company_metrics",
        "report_submissions",
        ["organization_id", "report_submission_id", "company_id", "reporting_period_id"],
        ["organization_id", "id", "company_id", "reporting_period_id"],
    )
    op.create_foreign_key(
        "fk_metric_period_same_org",
        "company_metrics",
        "reporting_periods",
        ["organization_id", "reporting_period_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_processing_log_same_org",
        "processing_logs",
        "report_submissions",
        ["organization_id", "submission_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_audit_user_same_org",
        "audit_logs",
        "users",
        ["organization_id", "user_id"],
        ["organization_id", "id"],
    )
    op.create_check_constraint(
        "ck_submission_valid_status",
        "report_submissions",
        "submission_status IN "
        "('submitted', 'processing', 'validation_failed', 'pending_review', 'approved', "
        "'rejected', 'superseded')",
    )
    op.create_index(
        "uq_approved_submission_company_period",
        "report_submissions",
        ["organization_id", "company_id", "reporting_period_id"],
        unique=True,
        postgresql_where=sa.text("submission_status = 'approved'"),
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index(
        "ix_reporting_periods_template_id", "reporting_periods", ["template_id"]
    )
    op.create_index(
        "ix_report_submissions_template_id", "report_submissions", ["template_id"]
    )
    op.create_index(
        "ix_company_metrics_report_submission_id",
        "company_metrics",
        ["report_submission_id"],
    )
    op.drop_constraint(
        "ck_nonnegative_financials", "company_metrics", type_="check"
    )
    op.drop_constraint("ck_nonnegative_counts", "company_metrics", type_="check")
    op.create_check_constraint(
        "ck_metric_nonnegative_revenue",
        "company_metrics",
        "revenue IS NULL OR revenue >= 0",
    )
    op.create_check_constraint(
        "ck_metric_nonnegative_expenses",
        "company_metrics",
        "expenses IS NULL OR expenses >= 0",
    )
    op.create_check_constraint(
        "ck_metric_nonnegative_cash",
        "company_metrics",
        "cash_balance IS NULL OR cash_balance >= 0",
    )
    op.create_check_constraint(
        "ck_metric_nonnegative_customers",
        "company_metrics",
        "customer_count IS NULL OR customer_count >= 0",
    )
    op.create_check_constraint(
        "ck_metric_nonnegative_new_customers",
        "company_metrics",
        "new_customers IS NULL OR new_customers >= 0",
    )
    op.create_check_constraint(
        "ck_metric_nonnegative_employees",
        "company_metrics",
        "employee_count IS NULL OR employee_count >= 0",
    )
    op.create_check_constraint(
        "ck_metric_new_customers_bounded",
        "company_metrics",
        "new_customers IS NULL OR customer_count IS NULL OR "
        "new_customers <= customer_count",
    )
    op.create_check_constraint(
        "ck_period_dates_ordered",
        "reporting_periods",
        "start_date <= end_date",
    )
    op.create_check_constraint(
        "ck_user_known_role",
        "users",
        "role IN ('admin', 'analyst', 'viewer', 'company_submitter')",
    )
    op.create_check_constraint(
        "ck_user_company_role_binding",
        "users",
        "(role = 'company_submitter' AND company_id IS NOT NULL) OR "
        "(role <> 'company_submitter' AND company_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_submission_context_complete",
        "report_submissions",
        "(company_id IS NULL AND reporting_period_id IS NULL) OR "
        "(company_id IS NOT NULL AND reporting_period_id IS NOT NULL)",
    )

    submissions = connection.execute(
        sa.text(
            "SELECT id, organization_id, submitted_by, submission_status "
            "FROM report_submissions ORDER BY submitted_at, id"
        )
    )
    for submission_id, organization_id, actor_id, status in submissions:
        connection.execute(
            sa.text(
                """
                INSERT INTO submission_events
                    (id, organization_id, submission_id, actor_id, previous_state,
                     new_state, reason, created_at)
                VALUES
                    (:id, :organization_id, :submission_id, :actor_id, NULL,
                     :new_state, 'Migrated legacy submission state', CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "organization_id": organization_id,
                "submission_id": submission_id,
                "actor_id": actor_id,
                "new_state": status,
            },
        )

    op.alter_column("reporting_periods", "template_id", nullable=False)
    op.alter_column("report_submissions", "template_id", nullable=False)


def downgrade():
    raise RuntimeError(
        "The reporting lifecycle migration is intentionally irreversible because "
        "it rewrites legacy submission states and permits multiple historical metrics."
    )
