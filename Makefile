PY=python
VENV=.venv
ENV?=dev
DB_URL?=postgresql://etl:etl@localhost:5432/dw

.PHONY: init deps fmt lint quality test seed etl incremental dq up down logs psql clean rebuild

init: deps
deps:
	[ -d $(VENV) ] || python -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt

fmt:
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/black .

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .
	$(VENV)/bin/sqlfluff lint sql

quality: lint test dq

test:
	$(VENV)/bin/pytest -m "unit"

itest:
	docker compose up -d postgres
	$(VENV)/bin/pytest -m "integration"
	docker compose down

seed:
	$(PY) scripts/generate_seed_data.py --out data/seeds

etl:
	$(PY) etl/pipelines/run.py --mode=full --env $(ENV)

incremental:
	$(PY) etl/pipelines/run.py --mode=incremental --env $(ENV)

dq:
	bash scripts/dq_checks.sh

up:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f postgres

psql:
	docker compose exec postgres psql -U etl -d dw

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache

rebuild: down clean up deps etl
