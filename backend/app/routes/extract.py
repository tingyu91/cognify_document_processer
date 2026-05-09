from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from app.services import ocr
from app.services.storage import validate_file
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["extract"])


class ExtractResponse(BaseModel):
    fields: dict
    extraction_failed: bool


@router.post("/extract", response_model=ExtractResponse, status_code=status.HTTP_200_OK)
async def extract_document(
    file: UploadFile = File(...),
):
    data = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    if mime_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=422, detail="Only JPEG and PNG images are supported for extraction")

    try:
        validate_file(data, mime_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        extracted = ocr.extract_fields(data, mime_type)
    except Exception:
        logger.exception("ocr_extract_endpoint_failed", extra={"mime_type": mime_type})
        raise HTTPException(status_code=500, detail="OCR processing failed")

    extraction_failed = not any(v is not None for v in extracted.values()) if extracted else True

    return ExtractResponse(fields=extracted, extraction_failed=extraction_failed)
