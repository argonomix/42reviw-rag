"""Initial ReviewRAG schema.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-06-09 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_name", sa.String(length=80), nullable=False),
        sa.Column("campus", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("reviewer_id_hash", sa.String(length=128), nullable=True),
        sa.Column("reviewee_id_hash", sa.String(length=128), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reviews_project_name", "reviews", ["project_name"])
    op.create_index("ix_reviews_campus", "reviews", ["campus"])
    op.create_index("ix_reviews_language", "reviews", ["language"])
    op.create_index("ix_reviews_passed", "reviews", ["passed"])

    op.create_table(
        "review_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "review_id",
            sa.String(),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("topic_label", sa.String(length=80), nullable=True),
        sa.Column("evaluation_axis", sa.String(length=80), nullable=True),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_review_chunks_review_id", "review_chunks", ["review_id"])
    op.create_index("ix_review_chunks_topic_label", "review_chunks", ["topic_label"])
    op.create_index("ix_review_chunks_language", "review_chunks", ["language"])

    op.create_table(
        "embeddings",
        sa.Column(
            "chunk_id",
            sa.String(),
            sa.ForeignKey("review_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_vector", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_embeddings_embedding_model", "embeddings", ["embedding_model"])

    op.create_table(
        "llm_evaluations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("chunk_id", sa.String(), nullable=True),
        sa.Column("answer_id", sa.String(), nullable=True),
        sa.Column("evaluation_type", sa.String(length=80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("llm_evaluations")
    op.drop_index("ix_embeddings_embedding_model", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_index("ix_review_chunks_language", table_name="review_chunks")
    op.drop_index("ix_review_chunks_topic_label", table_name="review_chunks")
    op.drop_index("ix_review_chunks_review_id", table_name="review_chunks")
    op.drop_table("review_chunks")
    op.drop_index("ix_reviews_passed", table_name="reviews")
    op.drop_index("ix_reviews_language", table_name="reviews")
    op.drop_index("ix_reviews_campus", table_name="reviews")
    op.drop_index("ix_reviews_project_name", table_name="reviews")
    op.drop_table("reviews")
