"""
Integration tests for OCR extraction.

Calls ocr.extract_fields() — the exact function used in production —
against real sample images. Requires ANTHROPIC_API_KEY in the environment.

Run from backend/:
    pytest tests/test_ocr.py -v
"""
import os
from pathlib import Path

import pytest

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample"

# Skip entire module if no API key — CI without secrets still passes
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


@pytest.fixture(scope="module")
def extract():
    """Import extract_fields once per module — loads agent file and Anthropic client."""
    from app.services.ocr import extract_fields
    return extract_fields


def _img(name: str) -> tuple[bytes, str]:
    path = SAMPLE_DIR / name
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return path.read_bytes(), mime


# ── Passports ──────────────────────────────────────────────────────────────

class TestPassports:
    def test_sg_passport_photo_page(self, extract):
        fields = extract(*_img("passport_photo_page.png"))
        assert fields.get("document_number"), "document_number missing"
        assert fields.get("full_name"), "full_name missing"
        assert fields.get("nationality"), "nationality missing"

    def test_sg_passport_full_scan(self, extract):
        fields = extract(*_img("singapore passport.jpg"))
        assert fields.get("document_number")
        assert fields.get("full_name")
        assert fields.get("date_of_expiry")

    def test_chinese_passport(self, extract):
        fields = extract(*_img("chinese passport.jpg"))
        assert fields.get("document_number")
        assert fields.get("full_name")
        assert fields.get("nationality")

    def test_uk_passport(self, extract):
        fields = extract(*_img("uk_passport.png"))
        assert fields.get("document_number")
        assert fields.get("full_name")
        assert fields.get("nationality")

    def test_hk_passport(self, extract):
        fields = extract(*_img("hong kong passport.jpg"))
        assert fields.get("document_number")
        assert fields.get("full_name")


# ── Other document types ────────────────────────────────────────────────────

class TestOtherDocuments:
    def test_sg_nric_front(self, extract):
        fields = extract(*_img("nric_front.png"))
        assert fields.get("document_number")
        assert fields.get("full_name")

    def test_sg_nric_back(self, extract):
        fields = extract(*_img("nric_back.png"))
        # Back has address but not always a name
        assert fields.get("document_number") or fields.get("full_address"), \
            "Neither document_number nor full_address found on NRIC back"

    def test_china_id_front(self, extract):
        fields = extract(*_img("china_id_front.png"))
        assert fields.get("document_number")
        assert fields.get("full_name")

    def test_hk_id_front(self, extract):
        fields = extract(*_img("hkid_front.png"))
        assert fields.get("document_number")
        assert fields.get("full_name")


# ── Extraction failure guard ────────────────────────────────────────────────

def test_returns_dict_not_empty_on_valid_image(extract):
    """Any valid document image should return at least one non-null field."""
    fields = extract(*_img("passport_photo_page.png"))
    non_null = [k for k, v in fields.items() if v is not None]
    assert non_null, f"All fields null — extraction failed. Raw fields: {fields}"


def test_returns_dict_type(extract):
    fields = extract(*_img("nric_front.png"))
    assert isinstance(fields, dict)
    assert set(fields.keys()) == {
        "full_name", "first_name", "last_name", "alias",
        "document_number", "date_of_issue", "date_of_expiry",
        "date_of_birth", "nationality", "full_address",
    }, "Response keys don't match expected schema"
