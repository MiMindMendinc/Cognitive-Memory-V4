.PHONY: install test demo api clean

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

demo:
	python examples/demo.py

api:
	python -m api.server

clean:
	rm -rf qdrant_data __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
