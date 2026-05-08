import uuid
import boto3
from botocore.config import Config
from app.config import settings

_ALLOWED_MIME = {"image/jpeg", "image/png", "application/pdf"}
_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"%PDF": "application/pdf",
}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def validate_file(data: bytes, declared_mime: str) -> str:
    """Check magic bytes and size. Returns detected mime type or raises ValueError."""
    if len(data) > _MAX_FILE_SIZE:
        raise ValueError("File exceeds 10 MB limit")
    for magic, mime in _MAGIC_BYTES.items():
        if data.startswith(magic):
            return mime
    raise ValueError("File type not allowed — only JPEG, PNG, PDF accepted")


def upload_document(data: bytes, mime_type: str) -> str:
    """Validate, then upload to R2. Returns the R2 key (UUID filename)."""
    detected = validate_file(data, mime_type)
    key = str(uuid.uuid4())
    _client().put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=data,
        ContentType=detected,
    )
    return key


def get_presigned_url(r2_key: str, expires_in: int = 900) -> str:
    """Generate a pre-signed download URL valid for expires_in seconds (default 15 min)."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": r2_key},
        ExpiresIn=expires_in,
    )


def delete_document(r2_key: str) -> None:
    _client().delete_object(Bucket=settings.r2_bucket_name, Key=r2_key)
