# smtp-protocol-implementation
SMTP Implementation for our class


# Email System Project - Makefile Guide

This project uses a `Makefile` to simplify virtual environment management, dependency installation, running the application, building documentation, and generating revision logs. This README explains each part of the Makefile and how to use it.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Makefile Workflow](#makefile-workflow)
  - [1. Create a Python Virtual Environment](#1-create-a-python-virtual-environment)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Freeze Dependencies](#3-freeze-dependencies)
  - [4. Run the Application](#4-run-the-application)
  - [5. Build Documentation](#5-build-documentation)
  - [6. Generate Revision Logs](#6-generate-revision-logs)
  - [7. Clean Build and Environment](#7-clean-build-and-environment)
- [Notes](#notes)

---

## Prerequisites

- Python 3.11 or newer
- `make` installed on your system
- Git installed (for revision logs)
- Internet access for installing Python packages

---

## Makefile Workflow

### 1. Create a Python Virtual Environment

```bash
make venv PYTHON=/path/to/python3.11
````

* Creates a virtual environment in the `.venv` directory.
* Saves the Python executable path in `.venv_python_path`.
* Checks that Python version is >= 3.11.
* **Important:** This step must be done first before any other commands.

### 2. Install Dependencies

```bash
make install
```

* Installs all Python packages listed in `requirements.txt`.
* Uses the Python executable from `.venv_python_path`.
* Upgrades `pip` automatically.

### 3. Freeze Dependencies

```bash
make freeze
```

* Regenerates `requirements.txt` from the virtual environment.
* Ensures the file matches the currently installed packages.
* Automatically uses the saved Python path.

### 4. Run the Application

```bash
make run
```

* Runs the main program located at `src/main.py`.
* Uses the Python executable from the venv.

### 5. Build Documentation

```bash
make docs
```

* Uses Sphinx to build HTML documentation from the `docs/` folder.
* Output is placed in `docs/_build/html`.

### 6. Generate Revision Logs

```bash
make revisions
```

* Writes a summary of Git commits to `revisions.txt`.

### 7. Clean Build and Environment

```bash
make clean
```

* Deletes the virtual environment `.venv`.
* Deletes built documentation in `docs/_build/`.
* Deletes `revisions.txt`.
* Deletes `.venv_python_path`.

---

## Notes

* The first time you create a venv, you **must** provide the Python executable with:

  ```bash
  make venv PYTHON=/usr/bin/python3.11
  ```

* After that, the Makefile will automatically read the saved Python executable path for all other commands.

* If you move or remove your Python executable, you will need to recreate the venv.

* Always ensure the virtual environment is active (or the Makefile will handle it for commands that use the venv).

---

This Makefile ensures consistent Python usage across development, testing, and documentation building, while simplifying dependency management and reproducibility.

