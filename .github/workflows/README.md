# GitHub Actions Workflows

This directory contains CI/CD workflows for the Kafka Lessons project.

## Workflows

### 1. `ci.yml` - Main CI Pipeline

Runs on every push and pull request to main/master/develop branches.

**Jobs:**
- **Format Check**: Validates code formatting with Black, isort, and flake8
- **Test**: Runs all tests (unit, integration, E2E) with Kafka services
- **Format and Test**: Final check that all jobs passed

**Features:**
- ✅ Code formatting validation
- ✅ Unit tests
- ✅ Integration tests (with Kafka)
- ✅ E2E tests (with Kafka)
- ✅ Test coverage reporting
- ✅ Codecov integration

### 2. `format.yml` - Auto-format Code

Manually triggered workflow that automatically formats code and commits changes.

**Usage:**
1. Go to Actions tab
2. Select "Auto-format Code"
3. Click "Run workflow"

**What it does:**
- Formats code with Black
- Sorts imports with isort
- Commits and pushes changes automatically

## Local Development

### Format Code Locally

```bash
# Install formatting tools
pip install black isort flake8

# Format code
black session_5/
isort session_5/

# Check formatting (without changing files)
black --check session_5/
isort --check-only session_5/

# Lint code
flake8 session_5/
```

### Run Tests Locally

```bash
# Make sure Kafka is running
docker ps | grep kafka

# Run all tests
cd session_5
pytest

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m e2e

# Run with coverage
pytest --cov=session_5 --cov-report=html
```

## Configuration

- **Black**: Configured in `pyproject.toml`
- **isort**: Configured in `pyproject.toml`
- **flake8**: Configured in `.flake8`
- **pytest**: Configured in `pyproject.toml` and `session_5/pytest.ini`

