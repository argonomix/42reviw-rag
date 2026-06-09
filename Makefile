COMPOSE = docker compose
COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml
HF_CACHE_VOLUME = reviewrag_huggingface_cache

.PHONY: up dev down logs test clean clean-all

up:
	$(COMPOSE) up --build

dev:
	$(COMPOSE_DEV) up --build

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
