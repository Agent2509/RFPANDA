# ===========================================================================
# RFPANDA — developer tasks
# Run `make` (or `make help`) to see everything available.
# ===========================================================================

SHELL := /bin/bash

# Use backend/.venv when present, otherwise fall back to an existing backend/venv.
VENV  := $(if $(wildcard backend/.venv/bin/python),backend/.venv,backend/venv)
PY    := $(VENV)/bin/python
PIP   := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn

.DEFAULT_GOAL := help

.PHONY: help setup backend-setup frontend-setup env dev backend frontend \
        test backend-test frontend-test typecheck build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: backend-setup frontend-setup env ## Install all dependencies and create .env files

backend-setup: ## Create the Python venv and install backend dependencies
	python3 -m venv backend/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

frontend-setup: ## Install frontend dependencies
	npm --prefix frontend install

env: ## Create .env files from the templates (only if missing)
	@test -f backend/.env || cp backend/.env.example backend/.env
	@test -f frontend/.env.local || cp frontend/.env.example frontend/.env.local
	@echo "Created backend/.env and frontend/.env.local — now fill in your keys."

dev: ## Run backend and frontend together (Ctrl+C stops both)
	@echo "Backend  -> http://localhost:8000"
	@echo "Frontend -> http://localhost:3000"
	@trap 'kill 0' EXIT INT TERM; \
	(cd backend && $(UVICORN) app.main:app --reload --port 8000) & \
	npm --prefix frontend run dev & \
	wait

backend: ## Run the backend only (auto-reload)
	cd backend && $(UVICORN) app.main:app --reload --port 8000

frontend: ## Run the frontend only
	npm --prefix frontend run dev

test: backend-test frontend-test ## Run all tests

backend-test: ## Run the backend test suite
	$(PY) -m pytest backend/tests -q

frontend-test: ## Run frontend unit tests
	npm --prefix frontend test

typecheck: ## Type-check the frontend
	npm --prefix frontend run typecheck

build: ## Production build of the frontend
	npm --prefix frontend run build

clean: ## Remove caches and build artifacts
	rm -rf backend/.pytest_cache .pytest_cache frontend/.next
	find . -type d -name __pycache__ \
		-not -path "*/node_modules/*" -not -path "*/.venv/*" \
		-prune -exec rm -rf {} +
