from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, ReportSubmission, SubmissionEvent, User

TRANSITIONS = {
    "submitted": {"processing"},
    "processing": {"validation_failed", "pending_review"},
    "validation_failed": set(),
    "pending_review": {"approved", "rejected"},
    "approved": {"superseded"},
    "rejected": set(),
    "superseded": set(),
}


def record_submission_event(
    db: Session,
    submission: ReportSubmission,
    actor: User,
    previous_state: str | None,
    new_state: str,
    reason: str | None = None,
) -> None:
    db.add(
        SubmissionEvent(
            organization_id=submission.organization_id,
            submission_id=submission.id,
            actor_id=actor.id,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
        )
    )
    db.add(
        AuditLog(
            organization_id=submission.organization_id,
            user_id=actor.id,
            action="submission_state_changed",
            entity_type="report_submission",
            entity_id=submission.id,
            details_json={
                "previous_state": previous_state,
                "new_state": new_state,
                "reason": reason,
            },
        )
    )


def transition_submission(
    db: Session,
    submission: ReportSubmission,
    actor: User,
    new_state: str,
    reason: str | None = None,
) -> None:
    previous_state = submission.submission_status
    if new_state not in TRANSITIONS.get(previous_state, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Submission cannot transition from {previous_state} to {new_state}",
        )
    submission.submission_status = new_state
    if new_state in {"approved", "rejected", "superseded"}:
        submission.decided_by = actor.id
        submission.decided_at = datetime.now(timezone.utc)
        submission.decision_reason = reason
    record_submission_event(
        db, submission, actor, previous_state, new_state, reason
    )


def mark_reviewed(
    db: Session, submission: ReportSubmission, actor: User, comment: str | None
) -> None:
    if submission.submission_status != "pending_review":
        raise HTTPException(
            status_code=409, detail="Only submissions pending review can be reviewed"
        )
    if submission.reviewed_at is not None:
        raise HTTPException(status_code=409, detail="Submission has already been reviewed")
    submission.reviewed_by = actor.id
    submission.reviewed_at = datetime.now(timezone.utc)
    record_submission_event(
        db,
        submission,
        actor,
        submission.submission_status,
        submission.submission_status,
        comment or "Analyst review completed",
    )


def approve_submission(
    db: Session,
    submission: ReportSubmission,
    actor: User,
    decision: str,
    reason: str | None,
) -> None:
    if submission.submission_status != "pending_review":
        raise HTTPException(
            status_code=409,
            detail="Only submissions pending review can be approved or rejected",
        )
    if submission.reviewed_at is None:
        raise HTTPException(
            status_code=409, detail="An analyst must review the submission first"
        )
    if decision == "rejected" and not (reason and reason.strip()):
        raise HTTPException(
            status_code=422, detail="A reason is required when rejecting a submission"
        )

    if decision == "approved":
        previous_approved = db.scalars(
            select(ReportSubmission).where(
                ReportSubmission.organization_id == submission.organization_id,
                ReportSubmission.company_id == submission.company_id,
                ReportSubmission.reporting_period_id == submission.reporting_period_id,
                ReportSubmission.submission_status == "approved",
                ReportSubmission.id != submission.id,
            )
        ).all()
        for prior in previous_approved:
            transition_submission(
                db,
                prior,
                actor,
                "superseded",
                f"Superseded by approved submission {submission.id}",
            )
        db.flush()

    transition_submission(db, submission, actor, decision, reason)
