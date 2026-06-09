import pytest
from pydantic import ValidationError

from app.schemas import RetrieveRequest


def test_retrieve_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        RetrieveRequest(query="   ")


def test_retrieve_request_strips_query() -> None:
    request = RetrieveRequest(query="  minishellで落ちやすいポイントは？  ")

    assert request.query == "minishellで落ちやすいポイントは？"
