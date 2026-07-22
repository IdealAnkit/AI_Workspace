"""create indexing tables

Revision ID: 20260723_05
Revises: 20260723_04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260723_05"
down_revision: Union[str, None] = "20260723_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("index_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vector_collection", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_version", sa.Integer(), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["processing_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_index_metadata_document_id", "index_metadata", ["document_id"])
    op.create_table("embedding_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("index_metadata_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["processing_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["index_metadata_id"], ["index_metadata.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_embedding_jobs_document_id", "embedding_jobs", ["document_id"])
    op.create_index("ix_embedding_jobs_index_metadata_id", "embedding_jobs", ["index_metadata_id"])
    op.create_index("ix_embedding_jobs_status", "embedding_jobs", ["status"])
    op.create_table("document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("embedding_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("index_metadata_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False), sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True), sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=512), nullable=True), sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True), sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["processing_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["embedding_job_id"], ["embedding_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["index_metadata_id"], ["index_metadata.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    for name, column in (("ix_document_chunks_document_id", "document_id"), ("ix_document_chunks_embedding_job_id", "embedding_job_id"), ("ix_document_chunks_index_metadata_id", "index_metadata_id"), ("ix_document_chunks_checksum", "checksum")):
        op.create_index(name, "document_chunks", [column])
    for table in ("embedding_logs", "embedding_errors"):
        op.create_table(table,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("embedding_job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("level" if table == "embedding_logs" else "error_type", sa.String(length=16 if table == "embedding_logs" else 128), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            *( [sa.Column("details", sa.JSON(), nullable=False)] if table == "embedding_errors" else [] ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["embedding_job_id"], ["embedding_jobs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(f"ix_{table}_embedding_job_id", table, ["embedding_job_id"])


def downgrade() -> None:
    for table in ("embedding_errors", "embedding_logs"):
        op.drop_index(f"ix_{table}_embedding_job_id", table_name=table); op.drop_table(table)
    for name in ("ix_document_chunks_checksum", "ix_document_chunks_index_metadata_id", "ix_document_chunks_embedding_job_id", "ix_document_chunks_document_id"):
        op.drop_index(name, table_name="document_chunks")
    op.drop_table("document_chunks")
    for name in ("ix_embedding_jobs_status", "ix_embedding_jobs_index_metadata_id", "ix_embedding_jobs_document_id"):
        op.drop_index(name, table_name="embedding_jobs")
    op.drop_table("embedding_jobs")
    op.drop_index("ix_index_metadata_document_id", table_name="index_metadata")
    op.drop_table("index_metadata")
