# Makefile for Multi-Environment Agentic Platform Docker Compose Orchestration

.PHONY: stage-build stage-start stage-stop stage-down staging-up staging-down prod-build prod-start prod-stop prod-down prod-up

PROD_COMPOSE = docker compose -f deploy/docker-compose.prod.yml --env-file deploy/env/.env.prod
BUILD_SERVICES = frontend api_server ai_agent mcp_server

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
prod-build:
	for service in $(BUILD_SERVICES); do \
		$(PROD_COMPOSE) build $$service; \
	done

prod-start:
	docker compose -f deploy/docker-compose.prod.yml --env-file deploy/env/.env.prod up

prod-stop:
	docker compose -f deploy/docker-compose.prod.yml stop

prod-down:
	docker compose -f deploy/docker-compose.prod.yml down --rmi all

prod-up: prod-start
