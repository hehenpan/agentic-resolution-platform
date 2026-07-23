# Makefile for Multi-Environment Agentic Platform Docker Compose Orchestration

.PHONY: staging-up staging-down prod-up prod-down

staging-up:
	docker compose -f deploy/docker-compose.staging.yml --env-file deploy/env/.env.staging up -d --build

staging-down:
	docker compose -f deploy/docker-compose.staging.yml down

prod-up:
	docker compose -f deploy/docker-compose.prod.yml --env-file deploy/env/.env.prod up -d --build

prod-down:
	docker compose -f deploy/docker-compose.prod.yml down
