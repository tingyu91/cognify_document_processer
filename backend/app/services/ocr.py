import base64
import json
import anthropic
from app.config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_SYSTEM_PROMPT = """You are a KYC document OCR system. Extract identity information from the provided document image.

Return ONLY a JSON object with these exact keys (use null for fields not visible):
{
  "first_name": string | null,
  "last_name": string | null,
  "id_number": string | null,
  "date_of_birth": string | null,  // ISO format: YYYY-MM-DD
  "nationality": string | null,
  "gender": string | null,
  "address": string | null,
  "document_type": string | null   // "National ID", "Passport", or "Driver License"
}

Rules:
- Return only the JSON object, no explanation or markdown
- Preserve exact formatting of ID numbers (spacing, dashes)
- For date_of_birth, convert to YYYY-MM-DD regardless of original format"""


def extract_fields(image_data: bytes, mime_type: str) -> dict:
    """Send document image to Claude Haiku and return extracted fields as a dict."""
    b64 = base64.standard_b64encode(image_data).decode()

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Prompt caching — ~90% cost reduction
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

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Return empty dict if model output is malformed — form data still saved from user input
        return {}
