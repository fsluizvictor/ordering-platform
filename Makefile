.PHONY: lint format typecheck test install

install:
	python -m pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy

test:
	pytest
