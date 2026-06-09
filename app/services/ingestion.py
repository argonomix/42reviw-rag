from sqlalchemy.orm import Session

from app.db.models import Embedding, Review, ReviewChunk
from app.rag.embeddings import embedding_service
from app.schemas import ReviewInput
from app.services.chunking import chunk_review
from app.services.normalization import load_records


def reset_data(db: Session) -> None:
    db.query(Embedding).delete()
    db.query(ReviewChunk).delete()
    db.query(Review).delete()
    db.commit()


def ingest_reviews(db: Session, records: list[ReviewInput]) -> tuple[int, int]:
    review_count = 0
    chunk_count = 0
    for record in records:
        review = Review(**record.model_dump())
        db.add(review)
        db.flush()
        review_count += 1

        for chunk_data in chunk_review(record):
            chunk = ReviewChunk(review_id=review.id, **chunk_data)
            db.add(chunk)
            db.flush()
            vector = embedding_service.embed(chunk.chunk_text)
            db.add(
                Embedding(
                    chunk_id=chunk.id,
                    embedding_model=embedding_service.model_name,
                    embedding_vector=vector,
                )
            )
            chunk_count += 1
    db.commit()
    return review_count, chunk_count


def ingest_path(db: Session, path: str) -> tuple[int, int]:
    return ingest_reviews(db, load_records(path))
