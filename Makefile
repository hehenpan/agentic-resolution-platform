# Makefile for Multi-Environment Agentic Platform Docker Compose Orchestration

.PHONY: stage-build stage-start stage-stop stage-down staging-up staging-down prod-up prod-down

# Staging commands
stage-build:
	docker compose -f deploy/docker-compose.staging.yml --env-file deploy/env/.env.staging build

stage-start:
	docker compose -f deploy/docker-compose.staging.yml --env-file deploy/env/.env.staging up

stage-stop:
	docker compose -f deploy/docker-compose.staging.yml stop

stage-down:
	docker compose -f deploy/docker-compose.staging.yml down --rmi all

# Aliases for backward compatibility
staging-up: stage-start
staging-down: stage-stop

# Production commands
prod-up:
	docker compose -f deploy/docker-compose.prod.yml --env-file deploy/env/.env.prod up -d --build

prod-down:
	docker compose -f deploy/docker-compose.prod.yml down
