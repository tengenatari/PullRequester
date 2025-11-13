
.PHONY: help build up down logs clean test test-unit test-e2e test-coverage status health

help:
	@echo "Available commands:"
	@echo "  build        - Build Docker images"
	@echo "  up           - Start services"
	@echo "  down         - Stop services"
	@echo "  logs         - Show application logs"
	@echo "  clean        - Stop and remove everything"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-e2e     - Run E2E tests only"
	@echo "  status       - Show service status"
	@echo "  health       - Check service health"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f web

clean:
	docker compose down -v
	docker system prune -f

test:
	docker compose exec web python manage.py test

test-unit:
	docker compose exec web python manage.py test api.tests.services

test-e2e:
	docker compose exec web python manage.py test api.tests.e2e

status:
	docker compose ps

health:
	curl -f http://localhost:8080/health || echo "Service is not healthy"