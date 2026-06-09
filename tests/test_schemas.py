import pytest
from pydantic import ValidationError

from app.schemas import RetrieveRequest


def test_retrieve_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        RetrieveRequest(query="   ")


def test_retrieve_request_strips_query() -> None:
    request = RetrieveRequest(query="  minishellで落ちやすいポイントは？  ")

    assert request.query == "minishellで落ちやすいポイントは？"


def test_retrieve_request_keeps_new_retrieval_options_optional() -> None:
    request = RetrieveRequest(query="pipe leak")

    assert request.retrieval_mode is None
    assert request.rerank is None


def test_retrieve_request_accepts_hybrid_options() -> None:
    request = RetrieveRequest(query="pipe leak", retrieval_mode="hybrid", rerank=True)

    assert request.retrieval_mode == "hybrid"
    assert request.rerank is True
