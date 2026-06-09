from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewInput(BaseModel):
    project_name: str
    campus: str = "42tokyo"
    language: str = "ja"
    reviewer_id_hash: str | None = None
    reviewee_id_hash: str | None = None
    score: int | None = Field(default=None, ge=0, le=125)
    passed: bool | None = None
    created_at: datetime | None = None
    raw_text: str
    source_type: str = "seed_json"
    source_payload: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    records: list[ReviewInput] | None = None
    path: str | None = None
    reset: bool = False


class IngestResponse(BaseModel):
    reviews: int
    chunks: int
    embedding_model: str


class QueryFilters(BaseModel):
    project_name: str | None = None
    campus: str | None = "42tokyo"
    language: str | None = "ja"
    passed: bool | None = None
    topic_label: str | None = None


class RetrieveRequest(BaseModel):
    query: str
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int = Field(default=8, ge=1, le=20)


class RetrievedChunk(BaseModel):
    id: str
    project_name: str
    campus: str
    language: str
    score: int | None
    passed: bool | None
    topic_label: str | None
    text: str
    similarity: float


class RetrieveResponse(BaseModel):
    retrieved_chunks: list[RetrievedChunk]
    latency_ms: int


class QueryResponse(RetrieveResponse):
    answer: str
    confidence: Literal["low", "medium", "high"]


class EvaluationResult(BaseModel):
    query: str
    expected_project: str
    expected_keywords: list[str]
    hit: bool
    keyword_hits: list[str]


class EvaluationResponse(BaseModel):
    cases: int
    retrieval_hit_rate: float
    keyword_hit_rate: float
    results: list[EvaluationResult]
