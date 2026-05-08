from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.submission import Submission

router = APIRouter(prefix="/api/v1", tags=["status"])


class StatusResponse(BaseModel):
    reference_number: str
    status: str
    rejection_reason: str | None
    created_at: str
    updated_at: str


@router.get("/status/{reference_number}", response_model=StatusResponse)
async def get_status(reference_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).where(Submission.reference_number == reference_number))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return StatusResponse(
        reference_number=submission.reference_number,
        status=submission.status,
        rejection_reason=submission.rejection_reason,
        created_at=submission.created_at.isoformat(),
        updated_at=submission.updated_at.isoformat(),
    )
