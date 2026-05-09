import base64
import io
import json
import re
import time
from pathlib import Path

import anthropic
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

_AGENT_FILE = Path(__file__).parent.parent.parent / "agents" / "identity_extractor.agent.md"

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _load_agent(path: Path) -> tuple[str, str, int]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    if len(parts) < 3:
        raise ValueError(f"Agent file missing YAML frontmatter: {path}")
    fm = parts[1]
    model = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE).group(1)
    max_tokens = int(re.search(r"^max_tokens:\s*(\d+)", fm, re.MULTILINE).group(1))
    return parts[2].strip(), model, max_tokens


_SYSTEM_PROMPT, _MODEL, _MAX_TOKENS = _load_agent(_AGENT_FILE)

# Anthropic internally scales images to ~1568px on the long side before counting tokens.
# Pre-resizing to this limit saves upload bandwidth without any quality loss.
# Going lower (e.g. 1200px) saves ~30% of image tokens while keeping text legible.
_MAX_LONG_SIDE = 1568


def _resize_for_ocr(image_data: bytes, mime_type: str) -> bytes:
    try:
        from PIL import Image
    except ImportError:
        return image_data

    img = Image.open(io.BytesIO(image_data))
    w, h = img.size
    long_side = max(w, h)
    if long_side <= _MAX_LONG_SIDE:
        return image_data

    scale = _MAX_LONG_SIDE / long_side
    new_w, new_h = round(w * scale), round(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    fmt = "JPEG" if mime_type == "image/jpeg" else "PNG"
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, format=fmt, quality=92, optimize=True)
    else:
        img.save(buf, format=fmt, optimize=True)
    resized = buf.getvalue()

    logger.debug(
        "ocr_image_resized",
        extra={
            "original_px": f"{w}x{h}",
            "resized_px": f"{new_w}x{new_h}",
            "original_bytes": len(image_data),
            "resized_bytes": len(resized),
        },
    )
    return resized


def extract_fields(image_data: bytes, mime_type: str) -> dict:
    """Send document image to Claude and return extracted KYC fields."""
    image_data = _resize_for_ocr(image_data, mime_type)
    image_size = len(image_data)
    logger.debug("ocr_request", extra={"mime_type": mime_type, "bytes": image_size, "model": _MODEL})

    b64 = base64.standard_b64encode(image_data).decode()
    t0 = time.monotonic()

    try:
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": "Extract the identity fields from this document."},
                    ],
                }
            ],
        )
    except Exception:
        logger.exception("ocr_api_error", extra={"mime_type": mime_type, "bytes": image_size})
        raise

    latency_ms = round((time.monotonic() - t0) * 1000)
    usage = response.usage
    logger.info(
        "ocr_response",
        extra={
            "model": response.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
            "latency_ms": latency_ms,
        },
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences the model occasionally adds despite instructions
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("ocr_json_parse_failed", extra={"raw": raw[:300]})
        return {}
