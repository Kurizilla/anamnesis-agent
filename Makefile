SHELL := /bin/bash
PROJECT_ROOT := $(shell pwd)

.PHONY: up down logs rebuild

up:
	@echo ">> Building and starting backend (FastAPI) and UI (Streamlit)"
	docker compose build --no-cache
	docker compose up -d
	@echo ">> Backend: http://localhost:8000  |  UI: http://localhost:8501"

rebuild:
	@echo ">> Rebuilding images (no cache) and restarting"
	docker compose down
	docker compose build --no-cache
	docker compose up -d

logs:
	docker compose logs -f clini_api

down:
	@echo ">> Stopping and removing containers"
	docker compose down 