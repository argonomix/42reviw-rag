import time

from sqlalchemy.orm import Session

from app.db.models import Embedding, Review, ReviewChunk
from app.rag.embeddings import embedding_service
from app.schemas import QueryFilters, RetrievedChunk


def retrieve_chunks(
    db: Session, query: str, filters: QueryFilters, top_k: int
) -> tuple[list[RetrievedChunk], int]:
    started = time.perf_counter()
    query_vector = embedding_service.embed(query)
    distance = Embedding.embedding_vector.cosine_distance(query_vector).label("distance")
    rows = (
        db.query(ReviewChunk, Review, distance)
        .join(Review, Review.id == ReviewChunk.review_id)
        .join(Embedding, Embedding.chunk_id == ReviewChunk.id)
    )
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

    ranked = []
    for chunk, review, distance_value in rows.order_by(distance).limit(top_k).all():
        similarity = 1.0 - float(distance_value or 0.0)
        ranked.append(
            RetrievedChunk(
                id=chunk.id,
                project_name=review.project_name,
                campus=review.campus,
                language=review.language,
                score=review.score,
                passed=review.passed,
                topic_label=chunk.topic_label,
                text=chunk.chunk_text,
                similarity=round(float(similarity), 4),
            )
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    return ranked, latency_ms
