"""add_documents_info

Revision ID: a1b2c3d4e5f6
Revises: 732b79026f46
Create Date: 2026-05-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '732b79026f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents_info",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("submission_id", UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        # OCR extracted fields — all nullable
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("first_name", sa.Text, nullable=True),
        sa.Column("last_name", sa.Text, nullable=True),
        sa.Column("alias", sa.Text, nullable=True),
        sa.Column("document_number", sa.Text, nullable=True),
        sa.Column("date_of_issue", sa.Text, nullable=True),
        sa.Column("date_of_expiry", sa.Text, nullable=True),
        sa.Column("date_of_birth", sa.Text, nullable=True),
        sa.Column("nationality", sa.Text, nullable=True),
        sa.Column("full_address", sa.Text, nullable=True),
        # Metadata
        sa.Column("raw_extraction", JSONB, nullable=True),
        sa.Column("extraction_failed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("user_approved", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_documents_info_document_id", "documents_info", ["document_id"])
    op.create_index("idx_documents_info_submission_id", "documents_info", ["submission_id"])


def downgrade() -> None:
    op.drop_index("idx_documents_info_submission_id", table_name="documents_info")
    op.drop_index("idx_documents_info_document_id", table_name="documents_info")
    op.drop_table("documents_info")
