from app.core.config import get_settings


class NoOpReranker:
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [0.0 for _ in texts]


class CrossEncoderReranker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.settings.reranker_model_name)
        scores = self._model.predict([(query, text) for text in texts])
        return [float(score) for score in scores]


def rerank_scores(query: str, texts: list[str], enabled: bool) -> list[float] | None:
    if not enabled:
        return None
    try:
        return CrossEncoderReranker().rerank(query, texts)
    except Exception:
        return None
