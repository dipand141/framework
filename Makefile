# ─────────────────────────────────────────────────────────────────────────────
# U-Ask QA Automation – Makefile
# ─────────────────────────────────────────────────────────────────────────────
VENV        := venv
PYTHON      := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
PYTEST      := $(VENV)/bin/pytest
ALLURE_DIR  := reports/allure-results
REPORT_DIR  := reports/allure-report

.DEFAULT_GOAL := help

# ─── Setup ───────────────────────────────────────────────────────────────────
.PHONY: install
install: ## Create venv and install all dependencies
	bash setup_venv.sh

# ─── Test Suites ─────────────────────────────────────────────────────────────
.PHONY: test
test: ## Run the full test suite
	$(PYTEST)

.PHONY: test-smoke
test-smoke: ## Run smoke tests only
	$(PYTEST) -m smoke

.PHONY: test-ui
test-ui: ## Run UI behaviour tests
	$(PYTEST) -m ui

.PHONY: test-ai
test-ai: ## Run AI response validation tests
	$(PYTEST) -m ai_validation

.PHONY: test-security
test-security: ## Run security / injection tests
	$(PYTEST) -m security

.PHONY: test-en
test-en: ## Run English-language tests
	$(PYTEST) -m english

.PHONY: test-ar
test-ar: ## Run Arabic-language tests
	$(PYTEST) -m arabic

.PHONY: test-mobile
test-mobile: ## Run mobile viewport tests
	MOBILE_EMULATION=true $(PYTEST) -m mobile

.PHONY: test-parallel
test-parallel: ## Run full suite in parallel (4 workers)
	$(PYTEST) -n 4

# ─── Reporting ───────────────────────────────────────────────────────────────
.PHONY: report
report: ## Generate & open Allure HTML report
	allure generate $(ALLURE_DIR) -o $(REPORT_DIR) --clean
	allure open $(REPORT_DIR)

.PHONY: report-serve
report-serve: ## Serve live Allure report from results directory
	allure serve $(ALLURE_DIR)

# ─── Linting ─────────────────────────────────────────────────────────────────
.PHONY: lint
lint: ## Run flake8 and black check
	$(VENV)/bin/flake8 . --max-line-length=120 --exclude=venv,reports
	$(VENV)/bin/black --check . --exclude venv

.PHONY: format
format: ## Auto-format code with black
	$(VENV)/bin/black . --exclude venv

# ─── Cleanup ─────────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove generated reports, cache, and pyc files
	rm -rf reports/allure-results/* reports/allure-report reports/screenshots
	find . -type d -name __pycache__ -not -path './venv/*' | xargs rm -rf
	find . -name '*.pyc' -not -path './venv/*' -delete
	rm -rf .pytest_cache

.PHONY: clean-all
clean-all: clean ## Also remove the virtual environment
	rm -rf $(VENV)

# ─── Help ────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
