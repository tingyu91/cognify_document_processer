import random
import string
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.submission import AuditLog, Submission
from app.services import crypto
from app.services.email import send_submission_confirmation
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["submit"])


class SubmitRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    nationality: str
    gender: str
    document_type: str
    id_number: str
    date_of_birth: str
    address: str
    city: str
    postal_code: str
    consent_given: bool


class SubmitResponse(BaseModel):
    reference_number: str
    message: str


def _generate_reference() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"KYC-{suffix}"


@router.post("/submit", response_model=SubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_kyc(payload: SubmitRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if not payload.consent_given:
        raise HTTPException(status_code=400, detail="Consent is required to proceed")

    # Generate collision-safe reference number
    for _ in range(5):
        ref = _generate_reference()
        existing = await db.execute(select(Submission).where(Submission.reference_number == ref))
        if not existing.scalar_one_or_none():
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique reference number")

    submission = Submission(
        reference_number=ref,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        nationality=payload.nationality,
        gender=payload.gender,
        document_type=payload.document_type,
        # Encrypt sensitive fields before storing
        id_number_enc=crypto.encrypt(payload.id_number),
        date_of_birth_enc=crypto.encrypt(payload.date_of_birth),
        phone_enc=crypto.encrypt(payload.phone),
        address_enc=crypto.encrypt(payload.address),
        city_enc=crypto.encrypt(payload.city),
        postal_code_enc=crypto.encrypt(payload.postal_code),
        consent_given=True,
        consent_timestamp=datetime.now(timezone.utc),
        status="pending",
    )
    db.add(submission)

    log = AuditLog(
        action="submission_created",
        entity_type="submission",
        entity_id=submission.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_value={"reference_number": ref, "email": payload.email},
    )
    db.add(log)
    await db.commit()

    try:
        send_submission_confirmation(
            to=payload.email,
            reference_number=ref,
            full_name=f"{payload.first_name} {payload.last_name}",
        )
    except Exception:
        logger.exception("email_send_failed", extra={"reference": ref, "email": payload.email})

    return SubmitResponse(reference_number=ref, message="Submission received. You will be notified by email.")
