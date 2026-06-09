import asyncio
import json

import pytest
from pydantic import ValidationError

from app.api import routes
from app.schemas import RetrievedChunk, RetrieveRequest


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, item) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commits += 1


def chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="chunk-1",
        project_name="minishell",
        campus="42tokyo",
        language="ja",
        score=80,
        passed=False,
        topic_label="signals",
        text="Ctrl-C handling differs from bash.",
        similarity=0.5,
        retrieval_source="keyword",
    )


async def response_events(response) -> list[dict]:
    body = ""
    async for item in response.body_iterator:
        body += item.decode() if isinstance(item, bytes) else item
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def test_query_stream_can_skip_generation(monkeypatch) -> None:
    db = FakeDb()
    called = False

    def fake_retrieve_chunks(*args):
        return [chunk()], 12

    async def fake_generate_answer(*args):
        nonlocal called
        called = True
        return "answer", "high"

    monkeypatch.setattr(routes, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(routes, "generate_answer", fake_generate_answer)

    response = asyncio.run(
        routes.query_stream(
            request=RetrieveRequest(query="pipe leak", generate_answer=False),
            db=db,
        )
    )

    events = asyncio.run(response_events(response))
    assert [event["event"] for event in events] == ["retrieval"]
    assert events[0]["retrieved_chunks"][0]["id"] == "chunk-1"
    assert called is False
    assert db.added == []
    assert db.commits == 0


def test_query_stream_returns_retrieval_before_answer(monkeypatch) -> None:
    db = FakeDb()

    def fake_retrieve_chunks(*args):
        return [chunk()], 12

    async def fake_generate_answer(*args):
        return "生成した回答", "high"

    monkeypatch.setattr(routes, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(routes, "generate_answer", fake_generate_answer)

    response = asyncio.run(
        routes.query_stream(
            request=RetrieveRequest(query="pipe leak", generate_answer=True),
            db=db,
        )
    )

    events = asyncio.run(response_events(response))
    assert [event["event"] for event in events] == ["retrieval", "answer"]
    assert events[0]["retrieved_chunks"][0]["id"] == "chunk-1"
    assert events[1]["answer"] == "生成した回答"
    assert len(db.added) == 1
    assert db.commits == 1


def test_query_stream_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        RetrieveRequest(query="   ")
