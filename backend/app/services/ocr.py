import base64
import json
import anthropic
from app.config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_SYSTEM_PROMPT = """You are a KYC document OCR system that handles documents in English, Simplified Chinese, and Traditional Chinese.

Return ONLY a JSON object with these exact keys (use null for fields not found):
{
  "full_name": "string or null",
  "first_name": "string or null",
  "last_name": "string or null",
  "alias": "string or null",
  "document_number": "string or null",
  "date_of_issue": "string or null",
  "date_of_expiry": "string or null",
  "date_of_birth": "string or null",
  "nationality": "string or null",
  "full_address": "string or null"
}

Rules:
- Return only the JSON object, no explanation or markdown
- Preserve Chinese characters in field values — do NOT transliterate unless the document itself provides romanized text
- For documents with both Chinese and English names (e.g. HK ID, Chinese passport), combine as: "中文名 / ENGLISH NAME"
- full_name is the complete name as it appears on the document; first_name and last_name are the component parts if identifiable
- alias is any "also known as" or 别名 field on the document
- document_number is any ID/license/passport/NRIC number that identifies this document (身份证号码, 护照号, etc.)
- Convert all date formats to YYYY-MM-DD (handle DD/MM/YYYY, MM/DD/YYYY, Chinese 年月日 formats like 2000年1月1日)
- nationality should be in English (convert 中国 → Chinese, 新加坡 → Singaporean, etc.)
- full_address should preserve the original language of the address
- Preserve exact formatting of document numbers (spacing, dashes, letters)
- If a field is not visible or not present on this document, return null — do not guess
- Recognized document types: Singapore NRIC (front/back), Singapore Passport, Singapore Driver's License, Mainland China 居民身份证, Hong Kong 香港身份證, Macau ID, Chinese Passport (中国护照)"""


def extract_fields(image_data: bytes, mime_type: str) -> dict:
    """Send document image to Claude Haiku and return extracted fields as a dict."""
    b64 = base64.standard_b64encode(image_data).decode()

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=768,
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
