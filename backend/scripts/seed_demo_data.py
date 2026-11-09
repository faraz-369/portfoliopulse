import calendar
from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.demo_accounts import DEMO_ORGANIZATION_SLUG, migrate_demo_account_emails
from app.db.session import SessionLocal
from app.models import Company, Organization, ReportingPeriod, User
from app.reporting_templates import ensure_default_template
from app.security import hash_password


def ensure_demo_seeding_allowed():
    if settings.environment != "development":
        raise RuntimeError("Demo seeding is available only in development.")
    if not settings.enable_demo_seeding:
        raise RuntimeError(
            "Demo seeding is disabled. Set ENABLE_DEMO_SEEDING=true explicitly."
        )


def main():
    ensure_demo_seeding_allowed()
    db = SessionLocal()
    try:
        migrate_demo_account_emails(db.connection())
        org = db.scalar(select(Organization).where(Organization.slug==DEMO_ORGANIZATION_SLUG))
        if not org:
            org = Organization(name="Demo Portfolio Organisation", slug=DEMO_ORGANIZATION_SLUG, description="Synthetic demonstration tenant")
            db.add(org)
            db.flush()
        for role, email, name in [
            ("admin","admin@portfoliopulse.example.com","Demo Administrator"),
            ("analyst","analyst@portfoliopulse.example.com","Demo Analyst"),
            ("viewer","viewer@portfoliopulse.example.com","Demo Viewer")]:
            if not db.scalar(select(User).where(User.organization_id==org.id, User.email==email)):
                db.add(User(organization_id=org.id, full_name=name, email=email, password_hash=hash_password(settings.demo_password), role=role))
        db.flush()
        template = ensure_default_template(db, org)
        companies = [
            ("ACME-001","Acme Cloud","SaaS"),("FIN-002","Northstar Finance","Fintech"),
            ("LOG-003","SwiftRoute Logistics","Logistics"),("HLT-004","WellSpring Digital","Healthcare technology"),
            ("ENG-005","Gridwise Energy","Energy technology"),("ENT-006","Meridian Systems","Enterprise software"),
            ("SAS-007","Orbit Metrics","SaaS"),("FIN-008","CedarPay","Fintech"),
            ("LOG-009","ParcelPilot","Logistics"),("HLT-010","PulseCare","Healthcare technology")]
        for ident,name,industry in companies:
            if not db.scalar(select(Company).where(Company.organization_id==org.id, Company.identifier==ident)):
                db.add(Company(organization_id=org.id, identifier=ident, slug=ident.lower(), name=name, industry=industry))
        for year in (2025, 2026):
            for month in range(1,13):
                if not db.scalar(select(ReportingPeriod).where(ReportingPeriod.organization_id==org.id, ReportingPeriod.year==year, ReportingPeriod.month==month)):
                    start=date(year,month,1)
                    end=date(year, month, calendar.monthrange(year, month)[1])
                    db.add(ReportingPeriod(organization_id=org.id,template_id=template.id,year=year,month=month,start_date=start,end_date=end))
        db.commit()
        print("Demo organisation, users, companies and reporting periods are ready.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
