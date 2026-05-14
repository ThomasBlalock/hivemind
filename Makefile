.PHONY: install test lint fmt corpus serve demo clean

install:
	uv pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests

fmt:
	ruff check --fix src tests

corpus:
	hivemind corpus build

serve:
	hivemind serve

demo:
	python scripts/compare_policies.py

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
