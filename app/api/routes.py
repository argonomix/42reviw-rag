import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Embedding, QueryLog, Review, ReviewChunk
from app.db.session import get_db
from app.rag.embeddings import embedding_service
from app.rag.generation import confidence_for, generate_answer
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
    chunks, latency_ms = retrieve_chunks(
        db,
        request.query,
        request.filters,
        request.top_k,
        request.retrieval_mode,
        request.rerank,
    )
    return RetrieveResponse(retrieved_chunks=chunks, latency_ms=latency_ms)


@router.post("/query", response_model=QueryResponse)
async def query(request: RetrieveRequest, db: Session = Depends(get_db)) -> QueryResponse:
    started = time.perf_counter()
    chunks, _ = retrieve_chunks(
        db,
        request.query,
        request.filters,
        request.top_k,
        request.retrieval_mode,
        request.rerank,
    )
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


def _stream_event(event: str, payload: dict) -> str:
    return json.dumps({"event": event, **payload}, ensure_ascii=False) + "\n"


@router.post("/query/stream")
async def query_stream(
    request: RetrieveRequest, db: Session = Depends(get_db)
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        started = time.perf_counter()
        try:
            chunks, retrieval_latency_ms = retrieve_chunks(
                db,
                request.query,
                request.filters,
                request.top_k,
                request.retrieval_mode,
                request.rerank,
            )
            confidence = confidence_for(chunks)
            yield _stream_event(
                "retrieval",
                {
                    "retrieved_chunks": [chunk.model_dump() for chunk in chunks],
                    "latency_ms": retrieval_latency_ms,
                    "confidence": confidence,
                },
            )

            if not request.generate_answer:
                return

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
            yield _stream_event(
                "answer",
                {
                    "answer": answer,
                    "latency_ms": latency_ms,
                    "confidence": confidence,
                },
            )
        except Exception:
            yield _stream_event(
                "error",
                {"detail": "検索または推論中にエラーが発生しました。"},
            )

    return StreamingResponse(events(), media_type="application/x-ndjson")


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
