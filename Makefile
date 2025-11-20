# ---------------------------
# User must provide:
#   make venv PYTHON=/path/to/python3.11
# ---------------------------

# Default venv directory
VENV_DIR := .venv
VENV_PY := $(VENV_DIR)/bin/python

# Detect if user passed PYTHON=
ifndef PYTHON
$(error You must specify the Python executable, e.g.: make venv PYTHON=/usr/bin/python3.11)
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
	@echo "Virtual environment created at $(VENV_DIR)."
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
	$(VENV_PY) main.py

# Build Sphinx docs
docs:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Error: venv missing. Run: make venv PYTHON=/path/to/python3.11"; \
		exit 1; \
	fi
	$(VENV_PY) -m sphinx -b html docs/ docs/_build/html
	@echo "Docs built at docs/_build/html"

# Generate revisions.txt (git log)
revisions:
	git log --oneline > revisions.txt
	@echo "Revisions written to revisions.txt"

# Clean build output and venv
clean:
	rm -rf $(VENV_DIR)
	rm -rf docs/_build
	rm -f revisions.txt
	@echo "Cleaned."

.PHONY: venv install freeze run docs clean revisions check_python
