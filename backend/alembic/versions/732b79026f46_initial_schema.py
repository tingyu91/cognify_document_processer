"""initial_schema

Revision ID: 732b79026f46
Revises:
Create Date: 2026-05-09 01:48:38.633901

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = '732b79026f46'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reference_number", sa.Text, unique=True, nullable=False),
        # Plaintext
        sa.Column("first_name", sa.Text, nullable=False),
        sa.Column("last_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("nationality", sa.Text, nullable=False),
        sa.Column("gender", sa.Text, nullable=False),
        sa.Column("document_type", sa.Text, nullable=False),
        # Encrypted
        sa.Column("id_number_enc", sa.Text, nullable=False),
        sa.Column("date_of_birth_enc", sa.Text, nullable=False),
        sa.Column("phone_enc", sa.Text, nullable=False),
        sa.Column("address_enc", sa.Text, nullable=False),
        sa.Column("city_enc", sa.Text, nullable=False),
        sa.Column("postal_code_enc", sa.Text, nullable=False),
        sa.Column("key_version", sa.Integer, nullable=False, server_default="1"),
        # Workflow
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        # PDPA
        sa.Column("consent_given", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('pending', 'under_review', 'approved', 'rejected')", name="ck_submissions_status"),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("r2_key", sa.Text, unique=True, nullable=False),
        sa.Column("mime_type", sa.Text, nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("key_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("admin_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.Text, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Indexes
    op.create_index("idx_submissions_email", "submissions", ["email"])
    op.create_index("idx_submissions_status", "submissions", ["status"])
    op.create_index("idx_submissions_reference_number", "submissions", ["reference_number"])
    op.create_index("idx_submissions_created_at", "submissions", [sa.text("created_at DESC")])
    op.create_index("idx_documents_submission_id", "documents", ["submission_id"])
    op.create_index("idx_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index("idx_audit_log_created_at", "audit_log", [sa.text("created_at DESC")])

    # Auto-update updated_at trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER submissions_updated_at
            BEFORE UPDATE ON submissions
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    """)

    # Row Level Security — service role key bypasses RLS automatically
    op.execute("ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS submissions_updated_at ON submissions;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at;")
    op.drop_table("audit_log")
    op.drop_table("documents")
    op.drop_table("submissions")
