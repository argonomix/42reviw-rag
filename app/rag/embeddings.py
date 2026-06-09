import hashlib
import math

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model_name = self.settings.embedding_model_name
        self.dimension = self.settings.embedding_dimension
        self._model = None

    def embed(self, text: str) -> list[float]:
        if self.settings.embedding_backend == "sentence-transformers":
            return self._embed_with_sentence_transformers(text)
        return self._embed_deterministically(text)

    def _embed_with_sentence_transformers(self, text: str) -> list[float]:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "EMBEDDING_BACKEND=sentence-transformers requires the ML dependencies. "
                    "Build the default semantic image, or use the lightweight compose override "
                    "with EMBEDDING_BACKEND=deterministic and RETRIEVAL_DEFAULT_MODE=keyword."
                ) from error

            self._model = SentenceTransformer(self.model_name)
        vector = self._model.encode([text], normalize_embeddings=True)[0]
        return [float(value) for value in vector]

    def _embed_deterministically(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = text.lower().replace("。", " ")
        word_tokens = [token for token in normalized.split() if token]
        compact = "".join(normalized.split())
        char_tokens = [compact[index : index + 2] for index in range(max(len(compact) - 1, 0))]
        char_tokens.extend(
            compact[index : index + 3] for index in range(max(len(compact) - 2, 0))
        )
        tokens = word_tokens + char_tokens
        if not tokens:
            tokens = list(text)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


embedding_service = EmbeddingService()
