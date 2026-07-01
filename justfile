# ============================================================================
# Setup & Environment
# ============================================================================

# Setup the development environment (dev deps only by default)
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v ssl-pydev >/dev/null 2>&1; then
        uv tool install ssl_pydev
    fi
    if ! command -v ssl-pydev >/dev/null 2>&1; then
        echo "error: ssl-pydev was installed but is not on PATH." >&2
        echo "check https://github.com/Swarm-Systems-Lab/ssl_pydev#install" >&2
        exit 1
    fi
    uv lock
    ssl-pydev setup-env

# Sync all dependency groups
sync:
    uv sync --frozen --all-extras

# Build and install the package in development mode
build:
    uv build

# ============================================================================
# Development & Code Quality
# ============================================================================

# Run linting and formatting checks
lint:
    uv run ruff format .
    uv run ruff check . --fix

# Run type checking
typecheck:
    uv run ty check src/ssl_vista

# Run pre-commit hooks on all files
pre-commit:
    uv run pre-commit run --all-files --show-diff-on-failure

# Run security scans with semgrep
security:
    ssl-pydev security

# ============================================================================
# Testing
# ============================================================================

# Run the app with an example preset
run:
    uv run sslvista -l 3d_canvas -data data_3d_test

# Run all tests with tox (recommended)
test:
    uv run tox -e tests

# Run tests in parallel, skip slow tests
test-fast:
    uv run tox -e tests-fast

# Run specific test by name
test-one TEST:
    uv run pytest tests/ -v -k "{{TEST}}"

# Run tests across multiple Python versions
test-multi-py:
    uv run tox -e py312,py313,py314

# List all available tox environments
list:
    uv run tox list

# ============================================================================
# Publishing
# ============================================================================

# Publish artifacts with uv (requires UV_PUBLISH_* env vars)
publish:
    ssl-pydev publish

# Publish artifacts with twine (CI-friendly; requires TWINE_* env vars)
publish-ci:
    ssl-pydev publish-ci

# ============================================================================
# Documentation
# ============================================================================

# Start the documentation server (serves while watching for changes)
docs:
    uv run --with '.[docs]' mkdocs serve --livereload

# Build documentation
docs-build:
    uv run tox -e docs

# Validate built documentation
validate-docs:
    ssl-pydev validate-docs

# Clean documentation build artifacts
clean-docs:
    rm -rf site

# ============================================================================
# CI Testing
# ============================================================================

# Test GitHub Actions workflows locally with act
act:
    ssl-pydev act

# ============================================================================
# Utilities
# ============================================================================

# Clean all build and test artifacts
clean:
    rm -rf build dist *.egg-info .pytest_cache .ruff_cache __pycache__ .venv cov.xml .coverage .tox .mypy_cache .test_projects
    rm -rf tests/.pytest_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ============================================================================
# Composite Commands
# ============================================================================

# Full CI simulation (do this before pushing!)
check-all: lint security typecheck pre-commit test
    @echo "All checks passed!"

# Show help information
help:
    @echo "ssl_simulator_vista Development Commands"
    @echo "========================================="
    @echo ""
    @echo "Setup & Environment:"
    @echo "  just setup          - Install dependencies with uv"
    @echo "  just sync           - Sync all dependency groups"
    @echo "  just build          - Build package in development mode"
    @echo ""
    @echo "Development & Code Quality:"
    @echo "  just lint           - Run ruff formatting and linting"
    @echo "  just typecheck      - Run type checking with ty"
    @echo "  just pre-commit     - Run pre-commit hooks on all files"
    @echo "  just security       - Run security scans with semgrep"
    @echo ""
    @echo "Testing:"
    @echo "  just test           - Run all tests with tox (recommended)"
    @echo "  just test-fast      - Run tests in parallel, skip slow tests"
    @echo "  just test-one TEST  - Run specific test by name"
    @echo "  just test-multi-py  - Run tests across Python 3.12-3.14"
    @echo "  just list           - List all tox environments"
    @echo ""
    @echo "Publishing:"
    @echo "  just publish        - Publish with uv"
    @echo "  just publish-ci     - Publish with twine (CI-friendly)"
    @echo ""
    @echo "Documentation:"
    @echo "  just docs           - Start documentation server"
    @echo "  just docs-build     - Build documentation"
    @echo "  just validate-docs  - Validate built documentation"
    @echo "  just clean-docs     - Clean documentation artifacts"
    @echo ""
    @echo "CI Testing:"
    @echo "  just act            - Test GitHub Actions workflows locally with act"
    @echo ""
    @echo "Utilities:"
    @echo "  just clean          - Clean build and test artifacts"
    @echo "  just check-all      - Run full CI simulation"
    @echo "  just help           - Show this help message"
