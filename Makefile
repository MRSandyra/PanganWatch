.PHONY: help setup up down ps logs lint test verify verify-phase versions report export contracts dq-docs docs clean

help:
	@echo "PanganWatch Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  setup         - Initial setup (install deps, init db)"
	@echo "  up            - Start all services"
	@echo "  down          - Stop all services"
	@echo "  ps            - Show service status"
	@echo "  logs          - Show service logs"
	@echo "  lint          - Run ruff linter"
	@echo "  test          - Run pytest"
	@echo "  verify        - Verify all phases"
	@echo "  verify-phase  - Verify specific phase (make verify-phase P=0)"
	@echo "  versions      - Generate VERSIONS.md"
	@echo "  report        - Generate HTML report"
	@echo "  export        - Export CSV for Tableau"
	@echo "  contracts     - Export Kafka contracts JSON Schema"
	@echo "  dq-docs       - Generate DQ rules documentation"
	@echo "  docs          - Generate all documentation"
	@echo "  clean         - Clean temporary files"

setup:
	uv sync
	@echo "Setup complete. Run 'make up' to start services."

up:
	docker compose up -d
	@echo "Services starting. Check status with 'make ps'"

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

test:
	uv run pytest -v

test-coverage:
	uv run pytest --cov=src/panganwatch --cov-report=html --cov-report=term

verify:
	uv run python scripts/verify.py --phase all

verify-phase:
	@if [ -z "$(P)" ]; then \
		echo "Error: Specify phase with P=<n>"; \
		echo "Example: make verify-phase P=0"; \
		exit 1; \
	fi
	uv run python scripts/verify.py --phase $(P)

versions:
	@echo "Generating VERSIONS.md..."
	@echo "# Versions" > docs/VERSIONS.md
	@echo "" >> docs/VERSIONS.md
	@echo "Generated: $$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> docs/VERSIONS.md
	@echo "" >> docs/VERSIONS.md
	@echo "## Python" >> docs/VERSIONS.md
	@uv run python --version >> docs/VERSIONS.md
	@echo "" >> docs/VERSIONS.md
	@echo "## Python packages" >> docs/VERSIONS.md
	@uv pip list >> docs/VERSIONS.md
	@echo "" >> docs/VERSIONS.md
	@echo "## Docker images" >> docs/VERSIONS.md
	@docker compose images >> docs/VERSIONS.md || echo "Docker compose not running" >> docs/VERSIONS.md
	@echo "VERSIONS.md generated"

contracts:
	@echo "Exporting Kafka contracts..."
	uv run python -m panganwatch.stream.export_schemas
	@echo "Contracts exported to contracts/"

dq-docs:
	@echo "Generating DQ documentation..."
	uv run python -m panganwatch.dq.engine generate-docs
	@echo "DQ docs generated"

docs:
	@echo "Generating all documentation..."
	$(MAKE) dq-docs
	$(MAKE) versions
	uv run python scripts/generate_docs.py
	@echo "All documentation generated"

report:
	@echo "Generating report..."
	uv run python -m panganwatch.analytics.report
	@echo "Report generated: reports/panganwatch_report.html"

export:
	@echo "Exporting CSV for Tableau..."
	uv run python -m panganwatch.analytics.export_bi
	@echo "CSV exported to exports/tableau/"

clean:
	rm -rf data/tmp/*
	rm -rf logs/*.log
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cleaned temporary files"
