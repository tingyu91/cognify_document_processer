from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.submission import AuditLog, Document, Submission
from app.services import crypto, storage
from app.services.email import send_status_update
from app.utils.auth import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class SubmissionSummary(BaseModel):
    id: str
    reference_number: str
    first_name: str
    last_name: str
    email: str
    nationality: str
    gender: str
    document_type: str
    status: str
    created_at: str


class SubmissionDetail(SubmissionSummary):
    id_number: str
    date_of_birth: str
    phone: str
    address: str
    city: str
    postal_code: str
    rejection_reason: str | None
    reviewed_at: str | None
    document_urls: list[str]


class UpdateStatusRequest(BaseModel):
    status: str
    rejection_reason: str | None = None


@router.get("/submissions", response_model=list[SubmissionSummary])
async def list_submissions(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin_id: str = Depends(require_admin),
):
    query = select(Submission).order_by(Submission.created_at.desc())
    if status_filter:
        query = query.where(Submission.status == status_filter)
    result = await db.execute(query)
    submissions = result.scalars().all()
    return [
        SubmissionSummary(
            id=str(s.id),
            reference_number=s.reference_number,
            first_name=s.first_name,
            last_name=s.last_name,
            email=s.email,
            nationality=s.nationality,
            gender=s.gender,
            document_type=s.document_type,
            status=s.status,
            created_at=s.created_at.isoformat(),
        )
        for s in submissions
    ]


@router.get("/submissions/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_id: str = Depends(require_admin),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")

    doc_result = await db.execute(select(Document).where(Document.submission_id == s.id))
    docs = doc_result.scalars().all()
    doc_urls = [storage.get_presigned_url(d.r2_key) for d in docs]

    log = AuditLog(
        action="document_accessed",
        entity_type="submission",
        entity_id=s.id,
        admin_user_id=admin_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(log)
    await db.commit()

    return SubmissionDetail(
        id=str(s.id),
        reference_number=s.reference_number,
        first_name=s.first_name,
        last_name=s.last_name,
        email=s.email,
        nationality=s.nationality,
        gender=s.gender,
        document_type=s.document_type,
        status=s.status,
        id_number=crypto.decrypt(s.id_number_enc),
        date_of_birth=crypto.decrypt(s.date_of_birth_enc),
        phone=crypto.decrypt(s.phone_enc),
        address=crypto.decrypt(s.address_enc),
        city=crypto.decrypt(s.city_enc),
        postal_code=crypto.decrypt(s.postal_code_enc),
        rejection_reason=s.rejection_reason,
        reviewed_at=s.reviewed_at.isoformat() if s.reviewed_at else None,
        document_urls=doc_urls,
        created_at=s.created_at.isoformat(),
    )


@router.patch("/submissions/{submission_id}/status", status_code=status.HTTP_200_OK)
async def update_status(
    submission_id: str,
    payload: UpdateStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_id: str = Depends(require_admin),
):
    allowed = {"pending", "under_review", "approved", "rejected"}
    if payload.status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")

    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")

    old_status = s.status
    s.status = payload.status
    s.rejection_reason = payload.rejection_reason
    s.reviewed_by = admin_id
    s.reviewed_at = datetime.now(timezone.utc)

    log = AuditLog(
        action="status_changed",
        entity_type="submission",
        entity_id=s.id,
        admin_user_id=admin_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_value={"status": old_status},
        new_value={"status": payload.status, "rejection_reason": payload.rejection_reason},
    )
    db.add(log)
    await db.commit()

    send_status_update(
        to=s.email,
        reference_number=s.reference_number,
        full_name=f"{s.first_name} {s.last_name}",
        status=payload.status,
        reason=payload.rejection_reason,
    )

    return {"message": f"Status updated to {payload.status}"}


@router.delete("/submissions/{submission_id}", status_code=status.HTTP_200_OK)
async def delete_submission(
    submission_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_id: str = Depends(require_admin),
):
    """Hard delete — PDPA right to erasure. Removes DB record and R2 documents."""
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Submission not found")

    doc_result = await db.execute(select(Document).where(Document.submission_id == s.id))
    for doc in doc_result.scalars().all():
        storage.delete_document(doc.r2_key)

    log = AuditLog(
        action="data_deleted",
        entity_type="submission",
        entity_id=s.id,
        admin_user_id=admin_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_value={"reference_number": s.reference_number, "email": s.email},
    )
    db.add(log)
    await db.delete(s)
    await db.commit()

    return {"message": "Submission and documents permanently deleted"}
