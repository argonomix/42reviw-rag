"""Add keyword terms for hybrid retrieval.

Revision ID: 0002_hybrid_retrieval_terms
Revises: 0001_initial_schema
Create Date: 2026-06-09 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0002_hybrid_retrieval_terms"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    chunk_columns = {column["name"] for column in inspector.get_columns("review_chunks")}
    if "search_token_count" not in chunk_columns:
        op.add_column(
            "review_chunks",
            sa.Column("search_token_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("review_chunks", "search_token_count", server_default=None)

    if not inspector.has_table("review_chunk_terms"):
        op.create_table(
            "review_chunk_terms",
            sa.Column(
                "chunk_id",
                sa.String(),
                sa.ForeignKey("review_chunks.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("term", sa.String(length=120), primary_key=True),
            sa.Column("term_frequency", sa.Integer(), nullable=False),
        )

    inspector = inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("review_chunk_terms")}
    if "ix_review_chunk_terms_chunk_id" not in indexes:
        op.create_index("ix_review_chunk_terms_chunk_id", "review_chunk_terms", ["chunk_id"])
    if "ix_review_chunk_terms_term" not in indexes:
        op.create_index("ix_review_chunk_terms_term", "review_chunk_terms", ["term"])


def downgrade() -> None:
    op.drop_index("ix_review_chunk_terms_term", table_name="review_chunk_terms")
    op.drop_index("ix_review_chunk_terms_chunk_id", table_name="review_chunk_terms")
    op.drop_table("review_chunk_terms")
    op.drop_column("review_chunks", "search_token_count")
