# Testing Guide

## Setup

pytest is already configured as a dev dependency in `pyproject.toml`.

Install dev dependencies with Poetry:
```bash
cd <repo-root>
poetry install --with dev
```

Or if already installed, make sure you're in the Poetry environment:
```bash
poetry shell
```

## Running Tests

### Run all tests:
```bash
poetry run pytest
```

### Run with verbose output:
```bash
poetry run pytest -v
```

### Run specific test file:
```bash
poetry run pytest test/test_metadata_creation.py
```

### Run specific test function:
```bash
poetry run pytest test/test_metadata_creation.py::test_metadata_file_creation
```

### Run with coverage report:
```bash
poetry run pytest --cov=API --cov-report=html
```

### Run from Poetry shell (no need for "poetry run" prefix):
```bash
poetry shell
pytest -v
```

## Test Structure

- `test/test_metadata_creation.py` - Tests for project metadata creation (9 tests)
  - `test_metadata_file_creation` - Verifies metadata file is created
  - `test_project_directory_structure` - Verifies directory structure
  - `test_metadata_required_fields` - Checks all required fields in project_metadata.json (including solver_parameters)
  - `test_metadata_values_correctness` - Validates specific values and solver parameters
  - `test_metadata_references_config_file` - Verifies reference to simulation_config.json
  - `test_read_simulation_config_function` - Tests read_simulation_config function
  - `test_read_metadata_function` - Tests read_metadata function
  - `test_metadata_with_none_project_dir` - Tests auto-detecting project dir
  - `test_metadata_json_validity` - Validates JSON format

## Fixtures

- `mock_config` - Mock InitialValues configuration
- `mock_gui_data` - Mock GUI JSON data
- `test_project_dir` - Temporary project directory (auto-cleaned)

## Notes

- All tests are located in the `test/` directory at the repo root
- Tests use temporary directories that are automatically cleaned up
- No simulation hardware required
- Tests are isolated and can run in any order
- All tests should pass for successful refactoring verification
- pytest 8.x is already configured in pyproject.toml
