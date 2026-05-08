from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.submission import Document, Submission
from app.services import storage, ocr

router = APIRouter(prefix="/api/v1", tags=["upload"])


class UploadResponse(BaseModel):
    document_id: str
    ocr_fields: dict


@router.post("/upload/{reference_number}", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    reference_number: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Submission).where(Submission.reference_number == reference_number))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    try:
        r2_key = storage.upload_document(data, mime_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    doc = Document(
        submission_id=submission.id,
        r2_key=r2_key,
        mime_type=mime_type,
        file_size_bytes=len(data),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Run OCR — non-blocking failure (form data is already saved)
    extracted = {}
    if mime_type in ("image/jpeg", "image/png"):
        try:
            extracted = ocr.extract_fields(data, mime_type)
        except Exception:
            pass

    return UploadResponse(document_id=str(doc.id), ocr_fields=extracted)
