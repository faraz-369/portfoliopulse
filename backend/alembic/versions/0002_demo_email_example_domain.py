from alembic import op

from app.demo_accounts import DEMO_EMAIL_MIGRATIONS, migrate_demo_account_emails

revision = "0002_demo_email_example_domain"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    migrate_demo_account_emails(op.get_bind())


def downgrade():
    migrate_demo_account_emails(
        op.get_bind(),
        {new_email: old_email for old_email, new_email in DEMO_EMAIL_MIGRATIONS.items()},
    )
