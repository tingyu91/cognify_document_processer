import json
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.submission import Document, DocumentInfo, Submission
from app.services import storage, ocr

router = APIRouter(prefix="/api/v1", tags=["upload"])


class UploadResponse(BaseModel):
    document_id: str
    ocr_fields: dict
    document_info_id: str | None = None


@router.post("/upload/{reference_number}", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    reference_number: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    approved_fields: str | None = Form(None),
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

    document_info_id = None
    if approved_fields is not None:
        try:
            fields_dict = json.loads(approved_fields)
            extraction_failed = not any(v is not None for v in fields_dict.values()) if fields_dict else True
            doc_info = DocumentInfo(
                document_id=doc.id,
                submission_id=submission.id,
                full_name=fields_dict.get("full_name"),
                first_name=fields_dict.get("first_name"),
                last_name=fields_dict.get("last_name"),
                alias=fields_dict.get("alias"),
                document_number=fields_dict.get("document_number"),
                date_of_issue=fields_dict.get("date_of_issue"),
                date_of_expiry=fields_dict.get("date_of_expiry"),
                date_of_birth=fields_dict.get("date_of_birth"),
                nationality=fields_dict.get("nationality"),
                full_address=fields_dict.get("full_address"),
                raw_extraction=fields_dict,
                extraction_failed=extraction_failed,
                user_approved=True,
                approved_at=datetime.now(),
            )
            db.add(doc_info)
            await db.commit()
            await db.refresh(doc_info)
            document_info_id = str(doc_info.id)
        except (json.JSONDecodeError, Exception):
            pass  # If saving info fails, don't fail the whole upload

    # Run OCR only if approved_fields not provided (avoid double processing)
    extracted = {}
    if approved_fields is None and mime_type in ("image/jpeg", "image/png"):
        try:
            extracted = ocr.extract_fields(data, mime_type)
        except Exception:
            pass

    return UploadResponse(document_id=str(doc.id), ocr_fields=extracted, document_info_id=document_info_id)
