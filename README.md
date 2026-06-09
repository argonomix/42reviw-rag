# ReviewRAG

Japanese-first RAG MVP for turning anonymized 42 Tokyo peer review feedback into searchable engineering knowledge.

## Stack

- FastAPI backend
- PostgreSQL + pgvector
- Ollama local generation, default model `qwen2.5:7b-instruct`
- Semantic embeddings with `sentence-transformers` and `intfloat/multilingual-e5-small`
- Hybrid retrieval with BM25-style keyword search + vector search
- Deterministic embedding fallback for local smoke tests

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`, click `Seed ingest`, then ask a Japanese review question.

The plain Compose command is the distribution-friendly default. For local development with a persistent Hugging Face model cache, use:

```bash
make dev
```

This keeps downloaded `sentence-transformers` models in the `reviewrag_huggingface_cache` Docker volume across rebuilds. `HF_TOKEN` in `.env` is optional; set it only if you want higher Hugging Face Hub rate limits and faster first-time downloads.

For better generation quality, pull the Ollama model once:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

Ollama generation requests default to a 180 second timeout. Override it in `.env` if
your local model needs longer:

```bash
OLLAMA_REQUEST_TIMEOUT_SECONDS=300
```

For NVIDIA GPU inference, install the NVIDIA Container Toolkit on the host, then run
the GPU Compose override:

```bash
make gpu
```

For the development workflow with both the Hugging Face cache and Ollama GPU access:

```bash
make dev-gpu
```

Check that Ollama can see the GPU with:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec ollama nvidia-smi
```

## API

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ingest -H 'Content-Type: application/json' -d '{"reset": true}'
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"minishellで落ちやすいポイントは？","filters":{"project_name":"minishell","campus":"42tokyo","language":"ja","passed":false},"top_k":8,"retrieval_mode":"hybrid"}'
```

`retrieval_mode` is optional and supports `vector`, `keyword`, or `hybrid`; the default is `hybrid`.
Set `"rerank": true` per request, or `RERANKER_ENABLED=true`, to rerank retrieved candidates with the configured cross-encoder model.

## Data Shape

The first ingestion target is JSON or JSONL exported from the 42 API and normalized into this canonical shape:

```json
{
  "project_name": "minishell",
  "campus": "42tokyo",
  "language": "ja",
  "reviewer_id_hash": "reviewer_001",
  "reviewee_id_hash": "reviewee_001",
  "score": 82,
  "passed": true,
  "created_at": "2026-06-09T00:00:00Z",
  "raw_text": "パイプ処理は概ね正しいが、heredoc の Ctrl-C 挙動が bash と異なる。",
  "source_type": "seed_json",
  "source_payload": {}
}
```

Unknown raw 42 API fields are preserved in `source_payload`.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

Docker workflow:

```bash
make up        # normal docker compose up --build
make dev       # compose with persistent Hugging Face cache
make clean     # remove only the opt-in Hugging Face cache volume
make clean-all # remove Compose volumes, including Postgres, Ollama, and the HF cache
```

The default embedding backend is `sentence-transformers`, using `intfloat/multilingual-e5-small`.
After changing embedding backends or models, re-ingest data with `{"reset": true}` or click `Seed ingest` so stored vectors match the active model.
After applying retrieval schema migrations, re-ingest data the same way so stored keyword term frequencies are populated.

Use `EMBEDDING_BACKEND=deterministic` only for lightweight local smoke tests that do not require semantic retrieval quality.
