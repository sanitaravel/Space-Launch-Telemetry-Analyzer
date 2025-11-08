# Running Tests for Space Launch Telemetry Analyzer

This directory contains tests for the Space Launch Telemetry Analyzer application using the `pytest` framework.

## Setup

Before running the tests, make sure you have installed the development dependencies:

```bash
# Activate your virtual environment
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate

# Install pytest if you haven't already
pip install pytest
```

## Running Tests with Clean Output

We've configured pytest to provide cleaner output by default, but you can use these options for different output styles:

```bash
# Most concise output - just dots for passed tests and details on failures
pytest -q

# Default configured output - moderately verbose
pytest

# Detailed output - shows all tests and their status
pytest -v

# Show only test failures
pytest -v --tb=short

# Show test progress with live output
pytest -xvs

# Filter out warning messages
pytest -v --disable-warnings
```

## Running Tests with Better Organization

To see tests organized by their folder structure:

```bash
# Run with verbose output and clear hierarchical structure
pytest -v

# Show as a compact tree structure
pytest --collect-only --tree

# Group test modules by their directory structure
pytest --collect-only -v

# Group output by modules (files) to avoid mixing test results
pytest --tb=native
```

## Filtering Tests

You can run specific test categories:

```bash
# Run only utility tests
pytest tests/test_utils

# Run only slow tests (marked with @pytest.mark.slow)
pytest -m "slow"

# Skip slow tests
pytest -m "not slow"
```

## Debug Tips

For debugging test failures:

```bash
# Enter debugger on first failure
pytest --pdb

# Show local variables in traceback
pytest --showlocals
```

## Generating Coverage Report

To check test coverage, first install the pytest-cov plugin:

```bash
# Install pytest-cov plugin
pip install pytest-cov
```

Then run pytest with coverage options:

```bash
# Get coverage report in terminal
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html
```

This will create a coverage report based on your project structure. The HTML report will be created in a directory called `htmlcov`.

## Test Structure

- `test_utils/`: Tests for utility functions
  - `test_validators.py`: Tests for input validation functions

## Adding New Tests

When adding new tests:

1. Create a new file in the appropriate directory with the prefix `test_`
2. Create test classes with the prefix `Test`
3. Create test functions with the prefix `test_`
4. Use clear, descriptive names for your test functions

## Best Practices

- Each test should test only one thing
- Use descriptive test names that explain what is being tested
- Use assertions to verify expected outcomes
- Keep tests independent of each other
