from datetime import datetime, timezone
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.session import Base


settings = get_settings()


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_name: Mapped[str] = mapped_column(String(80), index=True)
    campus: Mapped[str] = mapped_column(String(40), index=True, default="42tokyo")
    language: Mapped[str] = mapped_column(String(12), index=True, default="ja")
    reviewer_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewee_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, index=True, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), default="seed_json")
    source_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    chunks: Mapped[list["ReviewChunk"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewChunk(Base):
    __tablename__ = "review_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    topic_label: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    evaluation_axis: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language: Mapped[str] = mapped_column(String(12), index=True, default="ja")
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    search_token_count: Mapped[int] = mapped_column(Integer, default=0)

    review: Mapped[Review] = relationship(back_populates="chunks")
    embedding: Mapped["Embedding"] = relationship(
        back_populates="chunk", cascade="all, delete-orphan", uselist=False
    )
    search_terms: Mapped[list["ReviewChunkTerm"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )


class ReviewChunkTerm(Base):
    __tablename__ = "review_chunk_terms"

    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("review_chunks.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    term: Mapped[str] = mapped_column(String(120), primary_key=True, index=True)
    term_frequency: Mapped[int] = mapped_column(Integer)

    chunk: Mapped[ReviewChunk] = relationship(back_populates="search_terms")


class Embedding(Base):
    __tablename__ = "embeddings"

    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("review_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    embedding_model: Mapped[str] = mapped_column(String(160), index=True)
    embedding_vector: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimension))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    chunk: Mapped[ReviewChunk] = relationship(back_populates="embedding")


class LLMEvaluation(Base):
    __tablename__ = "llm_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    chunk_id: Mapped[str | None] = mapped_column(String, nullable=True)
    answer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    evaluation_type: Mapped[str] = mapped_column(String(80))
    score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    query_text: Mapped[str] = mapped_column(Text)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    answer_text: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
