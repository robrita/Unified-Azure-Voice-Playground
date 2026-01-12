# Makefile for Azure Personal Voice Playground
# Note: On Windows, you may need to install 'make' via chocolatey or use WSL

.PHONY: lint run check-and-run format install test test-unit test-integration test-cov test-fast push revert help

# Default target
help:
	@echo "Available commands:"
	@echo "  make lint          - Run Ruff linter"
	@echo "  make format        - Auto-fix linting issues and format code"
	@echo "  make run           - Start Streamlit app"
	@echo "  make check-and-run - Run linter, then start app (stops if linting fails)"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make push          - Stage, commit, and push changes (prompts for commit message)"
	@echo "  make revert        - Restore extract_results.json and clean temp JSON files"
	@echo ""
	@echo "Testing commands:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run only unit tests (fast, no Azure services)"
	@echo "  make test-integration - Run only integration tests (requires Azure credentials)"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-fast     - Run only fast tests (skip slow and integration)"

# Run linter
lint:
	uv run ruff check .

# Auto-fix and format
format:
	uv run ruff check --fix .
	uv run ruff format .

# Run Streamlit app
run:
	uv run streamlit run app.py

# Check linting then run (main workflow)
check-and-run: lint
	@echo "✅ Linting passed! Starting app..."
	uv run streamlit run app.py

# Install dependencies
install:
	uv sync

# Run all tests
test:
	uv run pytest

# Run only unit tests (fast, no external dependencies)
test-unit:
	uv run pytest -m unit -v

# Run only integration tests (requires Azure credentials)
test-integration:
	uv run pytest -m integration -v

# Run tests with coverage report
test-cov:
	uv run pytest --cov --cov-report=term-missing --cov-report=html

# Run fast tests only (skip slow and integration tests)
test-fast:
	uv run pytest -m "not slow and not integration" -v

# Stage, commit, and push changes (cross-platform)
push: revert
ifeq ($(OS),Windows_NT)
	@powershell -Command "$$msg = Read-Host 'Enter commit message'; git add . ; git commit -m \"$$msg\" ; git push"
else
	@read -p "Enter commit message: " msg; \
	git add . && \
	git commit -m "$$msg" && \
	git push
endif

# Revert extraction results and clean temp files (cross-platform)
revert:
ifeq ($(OS),Windows_NT)
	git restore .\outputs\extract_results.json
	@powershell -Command "Remove-Item -Path .\outputs\temp\*.json -Force -ErrorAction SilentlyContinue"
	@echo "✅ Reverted extract_results.json and cleaned temp JSON files"
else
	git restore ./outputs/extract_results.json
	rm -f ./outputs/temp/*.json
	@echo "✅ Reverted extract_results.json and cleaned temp JSON files"
endif
