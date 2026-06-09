COMPOSE = docker compose
COMPOSE_DEV = docker compose -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_GPU = docker compose -f docker-compose.yml -f docker-compose.gpu.yml
COMPOSE_DEV_GPU = docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.gpu.yml
HF_CACHE_VOLUME = reviewrag_huggingface_cache

.PHONY: up dev gpu dev-gpu down logs test clean clean-all

up:
	$(COMPOSE) up --build

dev:
	$(COMPOSE_DEV) up --build

gpu:
	$(COMPOSE_GPU) up --build

dev-gpu:
	$(COMPOSE_DEV_GPU) up --build

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
