from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://reviewrag:reviewrag@localhost:5432/reviewrag"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_request_timeout_seconds: float = 180.0
    embedding_backend: str = "sentence-transformers"
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_dimension: int = 384
    retrieval_default_mode: str = "hybrid"
    hybrid_vector_weight: float = 0.6
    hybrid_keyword_weight: float = 0.4
    hybrid_candidate_multiplier: int = 4
    reranker_enabled: bool = False
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    seed_data_path: str = "data/seed/reviews.json"
    eval_data_path: str = "data/eval/questions.json"
    default_campus: str = "42tokyo"
    default_language: str = "ja"
    hf_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
