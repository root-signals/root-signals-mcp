# RootSignals MCP Development Guide

## Build & Test Commands
- Install deps: `uv sync --extra dev"`
- Run server: `docker compose up`
- Run tests: `uv run pytest`
- Run single test: `uv run pytest tests/path/to/test.py::test_name -v`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run mypy .`

## Code Style Guidelines
- Use PEP 8 with 100 character line length
- Type hints required for all functions and variables
- Async-compatible code required
- Docstrings for all public APIs (classes, functions)
- Import order: stdlib → third-party → local
- Error handling: use explicit exception handling with detailed error messages
- Use Pydantic for data validation
- Follow existing patterns in the codebase
- Tests required for new features and bug fixes

## Environment
- Python 3.13+ required
- Manage dependencies with uv (not pip)
- Keep .env file with ROOT_SIGNALS_API_KEY for local development