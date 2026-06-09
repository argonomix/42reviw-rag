COMPOSE = docker compose
COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_GPU = docker compose -f docker-compose.yml -f docker-compose.gpu.yml
COMPOSE_DEV_GPU = docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.gpu.yml
COMPOSE_LIGHT = docker compose -f docker-compose.yml -f docker-compose.light.yml
HF_CACHE_VOLUME = reviewrag_huggingface_cache

.PHONY: up run rebuild ingest dev gpu dev-gpu run-gpu rebuild-gpu ingest-gpu light down logs test clean clean-all

up: run

run:
	$(COMPOSE_DEV) up

rebuild:
	$(COMPOSE_DEV) up --build

ingest:
	$(COMPOSE_DEV) up -d --build
	$(COMPOSE_DEV) exec -T api python -m app.services.ingestion_cli --reset

dev: rebuild

gpu: run-gpu

dev-gpu: rebuild-gpu

run-gpu:
	$(COMPOSE_DEV_GPU) up

rebuild-gpu:
	$(COMPOSE_DEV_GPU) up --build

ingest-gpu:
	$(COMPOSE_DEV_GPU) up -d --build
	$(COMPOSE_DEV_GPU) exec -T api python -m app.services.ingestion_cli --reset

light:
	$(COMPOSE_LIGHT) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

test:
	pytest

clean:
	$(COMPOSE_DEV) down --remove-orphans
	docker volume rm $(HF_CACHE_VOLUME) || true

clean-all:
	$(COMPOSE_DEV) down --volumes --remove-orphans
	docker volume rm $(HF_CACHE_VOLUME) || true
