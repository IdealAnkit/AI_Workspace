"""harden documents platform

Revision ID: 20260723_03
Revises: 20260723_02
Create Date: 2026-07-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_03"
down_revision: Union[str, Sequence[str], None] = "20260723_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The existing Phase 3 field is renamed instead of dropped, preserving data
    # while exposing a richer lifecycle through the application enum.
    op.alter_column(
        "documents",
        "upload_status",
        new_column_name="status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
    op.execute("UPDATE documents SET status = 'stored' WHERE status = 'uploaded'")
    op.alter_column(
        "documents",
        "status",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default="stored",
    )

    op.add_column(
        "documents",
        sa.Column("parent_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("documents", sa.Column("version", sa.Integer(), nullable=True, server_default="1"))
    op.add_column(
        "documents",
        sa.Column("is_latest_version", sa.Boolean(), nullable=True, server_default=sa.true()),
    )
    op.add_column(
        "documents",
        sa.Column("parent_folder_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "documents",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute("UPDATE documents SET uploaded_by = owner_id, updated_by = owner_id")
    op.alter_column("documents", "uploaded_by", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.create_foreign_key(
        op.f("fk_documents_parent_document_id_documents"),
        "documents",
        "documents",
        ["parent_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_documents_uploaded_by_users"),
        "documents",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_documents_updated_by_users"),
        "documents",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_documents_deleted_by_users"),
        "documents",
        "users",
        ["deleted_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)
    op.create_index(
        op.f("ix_documents_parent_document_id"), "documents", ["parent_document_id"], unique=False
    )
    op.create_index(op.f("ix_documents_parent_folder_id"), "documents", ["parent_folder_id"], unique=False)
    op.create_index(op.f("ix_documents_deleted_at"), "documents", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_documents_is_deleted"), "documents", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_is_deleted"), table_name="documents")
    op.drop_index(op.f("ix_documents_deleted_at"), table_name="documents")
    op.drop_index(op.f("ix_documents_parent_folder_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_parent_document_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_constraint(op.f("fk_documents_deleted_by_users"), "documents", type_="foreignkey")
    op.drop_constraint(op.f("fk_documents_updated_by_users"), "documents", type_="foreignkey")
    op.drop_constraint(op.f("fk_documents_uploaded_by_users"), "documents", type_="foreignkey")
    op.drop_constraint(op.f("fk_documents_parent_document_id_documents"), "documents", type_="foreignkey")
    op.drop_column("documents", "download_count")
    op.drop_column("documents", "last_accessed_at")
    op.drop_column("documents", "is_deleted")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "deleted_by")
    op.drop_column("documents", "updated_by")
    op.drop_column("documents", "uploaded_by")
    op.drop_column("documents", "parent_folder_id")
    op.drop_column("documents", "is_latest_version")
    op.drop_column("documents", "version")
    op.drop_column("documents", "parent_document_id")
    op.alter_column(
        "documents",
        "status",
        new_column_name="upload_status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default=None,
    )
