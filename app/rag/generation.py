import httpx

from app.core.config import get_settings
from app.schemas import RetrievedChunk


settings = get_settings()


def confidence_for(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "low"
    best = chunks[0].similarity
    if best >= 0.45 and len(chunks) >= 3:
        return "high"
    if best >= 0.2:
        return "medium"
    return "low"


def fallback_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "関連するレビュー根拠が見つかりませんでした。フィルタを緩めるか、別の表現で質問してください。"
    bullets = []
    for index, chunk in enumerate(chunks[:4], start=1):
        bullets.append(
            f"{index}. {chunk.project_name} / {chunk.topic_label}: {chunk.text[:140]}"
        )
    return (
        f"質問「{query}」に対して、取得したレビュー根拠から見る主なポイントは次の通りです。\n"
        + "\n".join(bullets)
        + "\n\nこれは取得されたレビュー断片に基づく要約です。"
    )


async def generate_answer(query: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
    confidence = confidence_for(chunks)
    if not chunks:
        return fallback_answer(query, chunks), confidence

    evidence = "\n".join(
        f"[{idx}] project={chunk.project_name}, score={chunk.score}, passed={chunk.passed}, "
        f"topic={chunk.topic_label}: {chunk.text}"
        for idx, chunk in enumerate(chunks[:8], start=1)
    )
    prompt = f"""
あなたは42 Tokyoのピアレビュー知識検索アシスタントです。
必ず日本語で回答してください。
回答は取得されたレビュー根拠だけに基づいてください。
推測する場合は「解釈」と明示してください。
最後に根拠番号を短く示してください。

質問:
{query}

レビュー根拠:
{evidence}
"""
    try:
        timeout = httpx.Timeout(settings.ollama_request_timeout_seconds, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
            if answer:
                return answer, confidence
    except httpx.HTTPError:
        pass
    return fallback_answer(query, chunks), confidence
