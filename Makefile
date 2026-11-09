.PHONY: test lint format migrate seed
test:
	cd backend && pytest -q
lint:
	cd backend && ruff check .
format:
	cd backend && ruff format .
migrate:
	cd backend && alembic upgrade head
seed:
	cd backend && python -m scripts.seed_demo_data
