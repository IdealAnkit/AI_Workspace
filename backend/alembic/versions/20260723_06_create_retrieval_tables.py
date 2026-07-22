"""create retrieval tables

Revision ID: 20260723_06
Revises: 20260723_05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_06"
down_revision: Union[str, None] = "20260723_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("retrieval_sessions", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("query", sa.Text(), nullable=False), sa.Column("top_k", sa.Integer(), nullable=False), sa.Column("filters", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_retrieval_sessions_user_id", "retrieval_sessions", ["user_id"]); op.create_index("ix_retrieval_sessions_workspace_id", "retrieval_sessions", ["workspace_id"])
    op.create_table("query_history", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("retrieval_session_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("query", sa.Text(), nullable=False), sa.Column("normalized_query", sa.Text(), nullable=False), sa.Column("retriever", sa.String(length=64), nullable=False), sa.Column("top_k", sa.Integer(), nullable=False), sa.Column("returned_chunks", sa.Integer(), nullable=False), sa.Column("duration_seconds", sa.Float(), nullable=False), sa.Column("filters", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["retrieval_session_id"], ["retrieval_sessions.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    for column in ("retrieval_session_id", "user_id", "workspace_id"): op.create_index(f"ix_query_history_{column}", "query_history", [column])
    op.create_table("retrieval_logs", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("retrieval_session_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("level", sa.String(length=16), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["retrieval_session_id"], ["retrieval_sessions.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_retrieval_logs_retrieval_session_id", "retrieval_logs", ["retrieval_session_id"])
    op.create_table("search_analytics", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("query", sa.Text(), nullable=False), sa.Column("retriever", sa.String(length=64), nullable=False), sa.Column("top_k", sa.Integer(), nullable=False), sa.Column("returned_chunks", sa.Integer(), nullable=False), sa.Column("duration_seconds", sa.Float(), nullable=False), sa.Column("filters", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_search_analytics_user_id", "search_analytics", ["user_id"]); op.create_index("ix_search_analytics_workspace_id", "search_analytics", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_search_analytics_workspace_id", table_name="search_analytics"); op.drop_index("ix_search_analytics_user_id", table_name="search_analytics"); op.drop_table("search_analytics")
    op.drop_index("ix_retrieval_logs_retrieval_session_id", table_name="retrieval_logs"); op.drop_table("retrieval_logs")
    for column in ("workspace_id", "user_id", "retrieval_session_id"): op.drop_index(f"ix_query_history_{column}", table_name="query_history")
    op.drop_table("query_history")
    op.drop_index("ix_retrieval_sessions_workspace_id", table_name="retrieval_sessions"); op.drop_index("ix_retrieval_sessions_user_id", table_name="retrieval_sessions"); op.drop_table("retrieval_sessions")
