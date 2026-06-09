import time
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.core.config import get_settings
from app.db.models import Embedding, Review, ReviewChunk, ReviewChunkTerm
from app.rag.embeddings import embedding_service
from app.rag.keyword import tokenize_for_search
from app.rag.reranking import rerank_scores
from app.schemas import QueryFilters, RetrievedChunk


settings = get_settings()
RRF_K = 60.0


@dataclass
class RetrievalCandidate:
    chunk: ReviewChunk
    review: Review
    final_score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    retrieval_source: str = "vector"


def retrieve_chunks(
    db: Session,
    query: str,
    filters: QueryFilters,
    top_k: int,
    retrieval_mode: str | None = None,
    rerank: bool | None = None,
) -> tuple[list[RetrievedChunk], int]:
    started = time.perf_counter()
    mode = retrieval_mode or settings.retrieval_default_mode
    if mode not in {"vector", "keyword", "hybrid"}:
        mode = "hybrid"

    candidate_limit = max(top_k, top_k * settings.hybrid_candidate_multiplier)
    if mode == "vector":
        candidates = _vector_candidates(db, query, filters, candidate_limit)
    elif mode == "keyword":
        candidates = _keyword_candidates(db, query, filters, candidate_limit)
    else:
        candidates = _hybrid_candidates(db, query, filters, candidate_limit)

    should_rerank = settings.reranker_enabled if rerank is None else rerank
    candidates = _maybe_rerank(query, candidates, should_rerank)
    ranked = [_to_retrieved_chunk(candidate) for candidate in candidates[:top_k]]
    latency_ms = int((time.perf_counter() - started) * 1000)
    return ranked, latency_ms


def _apply_filters(rows: Query, filters: QueryFilters) -> Query:
    if filters.project_name:
        rows = rows.filter(Review.project_name == filters.project_name.lower())
    if filters.campus:
        rows = rows.filter(Review.campus == filters.campus.lower())
    if filters.language:
        rows = rows.filter(Review.language == filters.language.lower())
    if filters.passed is not None:
        rows = rows.filter(Review.passed == filters.passed)
    if filters.topic_label:
        rows = rows.filter(ReviewChunk.topic_label == filters.topic_label)
    return rows


def _vector_candidates(
    db: Session, query: str, filters: QueryFilters, limit: int
) -> list[RetrievalCandidate]:
    query_vector = embedding_service.embed(query)
    distance = Embedding.embedding_vector.cosine_distance(query_vector).label("distance")
    rows = (
        db.query(ReviewChunk, Review, distance)
        .join(Review, Review.id == ReviewChunk.review_id)
        .join(Embedding, Embedding.chunk_id == ReviewChunk.id)
    )
    rows = _apply_filters(rows, filters)

    candidates: list[RetrievalCandidate] = []
    for chunk, review, distance_value in rows.order_by(distance).limit(limit).all():
        score = 1.0 - float(distance_value or 0.0)
        candidates.append(
            RetrievalCandidate(
                chunk=chunk,
                review=review,
                final_score=score,
                vector_score=score,
                retrieval_source="vector",
            )
        )
    return candidates


def _keyword_candidates(
    db: Session, query: str, filters: QueryFilters, limit: int
) -> list[RetrievalCandidate]:
    query_terms = sorted(set(tokenize_for_search(query)))
    if not query_terms:
        return []

    total_documents = _filtered_document_count(db, filters)
    if total_documents <= 0:
        return []
    average_document_length = _filtered_average_document_length(db, filters)

    df_rows = (
        db.query(
            ReviewChunkTerm.term.label("term"),
            func.count(ReviewChunkTerm.chunk_id).label("document_frequency"),
        )
        .join(ReviewChunk, ReviewChunk.id == ReviewChunkTerm.chunk_id)
        .join(Review, Review.id == ReviewChunk.review_id)
        .filter(ReviewChunkTerm.term.in_(query_terms))
    )
    df_rows = _apply_filters(df_rows, filters)
    document_frequency = df_rows.group_by(ReviewChunkTerm.term).subquery()

    tf = ReviewChunkTerm.term_frequency
    df = document_frequency.c.document_frequency
    dl = func.nullif(ReviewChunk.search_token_count, 0)
    idf = func.ln(1.0 + ((float(total_documents) - df + 0.5) / (df + 0.5)))
    denominator = tf + 1.5 * (0.25 + 0.75 * (dl / float(average_document_length)))
    score = func.sum(idf * ((tf * 2.5) / denominator)).label("keyword_score")

    rows = (
        db.query(ReviewChunk, Review, score)
        .join(Review, Review.id == ReviewChunk.review_id)
        .join(ReviewChunkTerm, ReviewChunkTerm.chunk_id == ReviewChunk.id)
        .join(document_frequency, document_frequency.c.term == ReviewChunkTerm.term)
        .filter(ReviewChunkTerm.term.in_(query_terms))
    )
    rows = _apply_filters(rows, filters)
    rows = rows.group_by(ReviewChunk.id, Review.id).order_by(score.desc()).limit(limit)

    candidates: list[RetrievalCandidate] = []
    max_score = 0.0
    for chunk, review, keyword_score in rows.all():
        raw_score = float(keyword_score or 0.0)
        max_score = max(max_score, raw_score)
        candidates.append(
            RetrievalCandidate(
                chunk=chunk,
                review=review,
                final_score=raw_score,
                keyword_score=raw_score,
                retrieval_source="keyword",
            )
        )
    if max_score > 0:
        for candidate in candidates:
            candidate.final_score = candidate.final_score / max_score
    return candidates


def _filtered_document_count(db: Session, filters: QueryFilters) -> int:
    rows = db.query(func.count(ReviewChunk.id)).join(Review, Review.id == ReviewChunk.review_id)
    rows = _apply_filters(rows, filters)
    return int(rows.scalar() or 0)


def _filtered_average_document_length(db: Session, filters: QueryFilters) -> float:
    rows = db.query(func.avg(ReviewChunk.search_token_count)).join(
        Review, Review.id == ReviewChunk.review_id
    )
    rows = _apply_filters(rows, filters)
    return float(rows.scalar() or 1.0)


def _hybrid_candidates(
    db: Session, query: str, filters: QueryFilters, limit: int
) -> list[RetrievalCandidate]:
    vector_candidates = _vector_candidates(db, query, filters, limit)
    keyword_candidates = _keyword_candidates(db, query, filters, limit)
    return fuse_candidates(
        vector_candidates,
        keyword_candidates,
        vector_weight=settings.hybrid_vector_weight,
        keyword_weight=settings.hybrid_keyword_weight,
    )[:limit]


def fuse_candidates(
    vector_candidates: list[RetrievalCandidate],
    keyword_candidates: list[RetrievalCandidate],
    *,
    vector_weight: float,
    keyword_weight: float,
) -> list[RetrievalCandidate]:
    by_id: dict[str, RetrievalCandidate] = {}
    fused_scores: dict[str, float] = {}

    for rank, candidate in enumerate(vector_candidates, start=1):
        by_id[candidate.chunk.id] = RetrievalCandidate(
            chunk=candidate.chunk,
            review=candidate.review,
            final_score=0.0,
            vector_score=candidate.vector_score,
            retrieval_source="vector",
        )
        fused_scores[candidate.chunk.id] = fused_scores.get(candidate.chunk.id, 0.0) + (
            vector_weight / (RRF_K + rank)
        )

    for rank, candidate in enumerate(keyword_candidates, start=1):
        existing = by_id.get(candidate.chunk.id)
        if existing is None:
            existing = RetrievalCandidate(
                chunk=candidate.chunk,
                review=candidate.review,
                final_score=0.0,
                retrieval_source="keyword",
            )
            by_id[candidate.chunk.id] = existing
        elif existing.retrieval_source == "vector":
            existing.retrieval_source = "hybrid"
        existing.keyword_score = candidate.keyword_score
        fused_scores[candidate.chunk.id] = fused_scores.get(candidate.chunk.id, 0.0) + (
            keyword_weight / (RRF_K + rank)
        )

    for chunk_id, candidate in by_id.items():
        candidate.final_score = fused_scores.get(chunk_id, 0.0)

    return sorted(by_id.values(), key=lambda candidate: candidate.final_score, reverse=True)


def _maybe_rerank(
    query: str, candidates: list[RetrievalCandidate], enabled: bool
) -> list[RetrievalCandidate]:
    scores = rerank_scores(query, [candidate.chunk.chunk_text for candidate in candidates], enabled)
    if scores is None or len(scores) != len(candidates):
        return candidates

    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    span = max_score - min_score
    for candidate, score in zip(candidates, scores, strict=True):
        candidate.rerank_score = float(score)
        candidate.final_score = 1.0 if span == 0 else (float(score) - min_score) / span
    return sorted(candidates, key=lambda candidate: candidate.final_score, reverse=True)


def _to_retrieved_chunk(candidate: RetrievalCandidate) -> RetrievedChunk:
    return RetrievedChunk(
        id=candidate.chunk.id,
        project_name=candidate.review.project_name,
        campus=candidate.review.campus,
        language=candidate.review.language,
        score=candidate.review.score,
        passed=candidate.review.passed,
        topic_label=candidate.chunk.topic_label,
        text=candidate.chunk.chunk_text,
        similarity=round(candidate.final_score, 4),
        vector_score=_rounded(candidate.vector_score),
        keyword_score=_rounded(candidate.keyword_score),
        rerank_score=_rounded(candidate.rerank_score),
        retrieval_source=candidate.retrieval_source,
    )


def _rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)
