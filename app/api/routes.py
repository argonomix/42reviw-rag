import time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Embedding, QueryLog, Review, ReviewChunk
from app.db.session import get_db
from app.rag.embeddings import embedding_service
from app.rag.generation import generate_answer
from app.rag.retrieval import retrieve_chunks
from app.schemas import (
    EvaluationResponse,
    IngestRequest,
    IngestResponse,
    QueryResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.services.evaluation import run_evaluation
from app.services.ingestion import ingest_path, ingest_reviews, reset_data


router = APIRouter()
settings = get_settings()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(select(func.now()))
    return {
        "status": "ok",
        "campus": settings.default_campus,
        "language": settings.default_language,
        "embedding_backend": settings.embedding_backend,
        "embedding_model": embedding_service.model_name,
    }


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    if request.reset:
        reset_data(db)
    if request.records is not None:
        review_count, chunk_count = ingest_reviews(db, request.records)
    else:
        review_count, chunk_count = ingest_path(db, request.path or settings.seed_data_path)
    return IngestResponse(
        reviews=review_count,
        chunks=chunk_count,
        embedding_model=embedding_service.model_name,
    )


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(request: RetrieveRequest, db: Session = Depends(get_db)) -> RetrieveResponse:
    chunks, latency_ms = retrieve_chunks(db, request.query, request.filters, request.top_k)
    return RetrieveResponse(retrieved_chunks=chunks, latency_ms=latency_ms)


@router.post("/query", response_model=QueryResponse)
async def query(request: RetrieveRequest, db: Session = Depends(get_db)) -> QueryResponse:
    started = time.perf_counter()
    chunks, _ = retrieve_chunks(db, request.query, request.filters, request.top_k)
    answer, confidence = await generate_answer(request.query, chunks)
    latency_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        QueryLog(
            query_text=request.query,
            filters=request.filters.model_dump(exclude_none=True),
            retrieved_chunk_ids=[chunk.id for chunk in chunks],
            answer_text=answer,
            latency_ms=latency_ms,
        )
    )
    db.commit()
    return QueryResponse(
        answer=answer,
        confidence=confidence,
        retrieved_chunks=chunks,
        latency_ms=latency_ms,
    )


@router.post("/evaluate", response_model=EvaluationResponse)
def evaluate(db: Session = Depends(get_db)) -> EvaluationResponse:
    return run_evaluation(db)


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    return {
        "reviews": db.query(Review).count(),
        "chunks": db.query(ReviewChunk).count(),
        "embeddings": db.query(Embedding).count(),
        "queries": db.query(QueryLog).count(),
    }
