install:
	pip install -r requirements.txt

lint:
	ruff check .
	ruff format . --diff
	mypy .

lint-fix:
	ruff format .
	ruff check . --fix

clean:
	rm -rf .mypy_cache
	rm -rf .ruff_cache
