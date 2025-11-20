# ---------------------------
# User must provide:
#   make venv PYTHON=/path/to/python3.11
# ---------------------------

VENV_DIR := .venv
PYTHON_FILE := .venv_python_path
VENV_PY := $(VENV_DIR)/bin/python

# Get the Python executable
ifeq ($(wildcard $(PYTHON_FILE)),)
    # If file doesn't exist, require user to pass PYTHON=
    ifndef PYTHON
        $(error You must specify the Python executable, e.g.: make venv PYTHON=/usr/bin/python3.11)
    endif
else
    PYTHON := $(shell cat $(PYTHON_FILE))
endif

# Rule: ensure Python version is >= 3.11
check_python:
	@echo "Checking Python version for: $(PYTHON)"
	@if ! $(PYTHON) -c 'import sys; exit(0 if sys.version_info >= (3,11) else 1)'; then \
		echo "Error: Python must be version 3.11 or newer."; \
		exit 1; \
	fi
	@echo "Python version OK."

# Create venv using user-supplied Python
venv: check_python
	@echo "Creating venv using $(PYTHON)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo $(PYTHON) > $(PYTHON_FILE)
	@echo "Virtual environment created at $(VENV_DIR)."
	@echo "Saved Python path to $(PYTHON_FILE)."
	@echo "Run: source $(VENV_DIR)/bin/activate"

# Install dependencies
install:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements.txt

# Regenerate requirements.txt (MUST use venv)
freeze:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m pip freeze > requirements.txt
	@echo "Updated requirements.txt"

# Run the program
run:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m src.main


# Build Sphinx docs
sphinx_docs:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m sphinx -b html docs/ docs/_build/html
	@echo "Docs built at docs/_build/html"

# Generate revisions.txt (git log)
revisions:
	git log > revisions.txt
	@echo "Revisions written to revisions.txt"

# Clean build output and venv
clean:
	rm -rf $(VENV_DIR)
	rm -rf docs/_build
	rm -f revisions.txt
	rm -f $(PYTHON_FILE)
	@echo "Cleaned."

format:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m black src tests
	@echo "Code formatted with black."

coverage:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m pytest --cov=src --cov-report=html
	@echo "Coverage report generated at htmlcov/index.html"


sync_repo:
	@set -e; \
	read -p "Enter commit message: " msg; \
	if [ -z "$$msg" ]; then \
		echo "Aborting: commit message cannot be empty."; \
		exit 1; \
	fi; \
	git add .; \
	git commit -m "$$msg"; \
	make revisions; \
	git push;


.PHONY: venv install freeze run sphinx_docs clean revisions check_python format coverage sync_repo
