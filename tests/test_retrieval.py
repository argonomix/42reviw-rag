from app.db.models import Review, ReviewChunk
from app.rag import retrieval
from app.rag.retrieval import RetrievalCandidate, fuse_candidates, retrieve_chunks
from app.schemas import QueryFilters


def candidate(chunk_id: str, source: str, score: float) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk=ReviewChunk(
            id=chunk_id,
            review_id="review-1",
            chunk_text=f"text {chunk_id}",
            chunk_index=0,
            language="ja",
            token_count=2,
            search_token_count=2,
        ),
        review=Review(
            id=f"review-{chunk_id}",
            project_name="minishell",
            campus="42tokyo",
            language="ja",
            raw_text=f"text {chunk_id}",
            source_type="test",
            source_payload={},
        ),
        final_score=score,
        vector_score=score if source == "vector" else None,
        keyword_score=score if source == "keyword" else None,
        retrieval_source=source,
    )


def test_fuse_candidates_marks_shared_hits_as_hybrid() -> None:
    fused = fuse_candidates(
        [candidate("shared", "vector", 0.9), candidate("vector-only", "vector", 0.8)],
        [candidate("shared", "keyword", 2.0), candidate("keyword-only", "keyword", 1.0)],
        vector_weight=0.6,
        keyword_weight=0.4,
    )

    by_id = {item.chunk.id: item for item in fused}
    assert by_id["shared"].retrieval_source == "hybrid"
    assert by_id["shared"].vector_score == 0.9
    assert by_id["shared"].keyword_score == 2.0


def test_retrieve_chunks_uses_keyword_mode(monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "_keyword_candidates", lambda *args: [candidate("kw", "keyword", 1.0)])

    chunks, _ = retrieve_chunks(
        db=None,
        query="pipe",
        filters=QueryFilters(),
        top_k=1,
        retrieval_mode="keyword",
        rerank=False,
    )

    assert chunks[0].id == "kw"
    assert chunks[0].retrieval_source == "keyword"


def test_retrieve_chunks_hybrid_rerank_falls_back_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "_hybrid_candidates", lambda *args: [candidate("hy", "hybrid", 0.5)])
    monkeypatch.setattr(retrieval, "rerank_scores", lambda *args: None)

    chunks, _ = retrieve_chunks(
        db=None,
        query="pipe",
        filters=QueryFilters(),
        top_k=1,
        retrieval_mode="hybrid",
        rerank=True,
    )

    assert chunks[0].id == "hy"
    assert chunks[0].similarity == 0.5
    assert chunks[0].rerank_score is None
