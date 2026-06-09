import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.retrieval import retrieve_chunks
from app.schemas import EvaluationResponse, EvaluationResult, QueryFilters


settings = get_settings()


def run_evaluation(db: Session) -> EvaluationResponse:
    cases = json.loads(Path(settings.eval_data_path).read_text(encoding="utf-8"))
    results: list[EvaluationResult] = []
    total_keyword_hits = 0
    total_keywords = 0
    for case in cases:
        filters = QueryFilters(**case.get("filters", {}))
        chunks, _ = retrieve_chunks(db, case["query"], filters, case.get("top_k", 5))
        expected_project = case["expected_project"]
        expected_keywords = case.get("expected_keywords", [])
        combined = "\n".join(chunk.text for chunk in chunks)
        keyword_hits = [keyword for keyword in expected_keywords if keyword in combined]
        total_keyword_hits += len(keyword_hits)
        total_keywords += len(expected_keywords)
        results.append(
            EvaluationResult(
                query=case["query"],
                expected_project=expected_project,
                expected_keywords=expected_keywords,
                hit=any(chunk.project_name == expected_project for chunk in chunks),
                keyword_hits=keyword_hits,
            )
        )

    retrieval_hits = sum(1 for result in results if result.hit)
    return EvaluationResponse(
        cases=len(results),
        retrieval_hit_rate=retrieval_hits / len(results) if results else 0.0,
        keyword_hit_rate=total_keyword_hits / total_keywords if total_keywords else 0.0,
        results=results,
    )
