# Testing Guide

This document provides information about the test suite for the catdroool-shipping project.

## Quick Start

### Running Tests

```bash
# Using just (recommended)
just test

# Or using pytest directly
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/services/test_aws.py -v

# Run specific test
python -m pytest tests/services/test_aws.py::test_aws_init_success -v
```

### Installing Dependencies

```bash
# Install all dependencies including test dependencies
pip install -r requirements.txt

# Or using pipenv
pipenv install --dev
pipenv shell
```

## Test Suite Overview

The test suite contains **78 tests** covering:
- Service layer modules
- Common utilities
- Integration points

### Test Statistics
- **Total Tests**: 78
- **Test Files**: 11
- **Pass Rate**: 100%
- **Execution Time**: ~0.5 seconds

## Test Structure

```
tests/
├── common/                      # Common utilities tests (13 tests)
│   ├── test_singleton.py        # Singleton pattern tests (3)
│   └── test_utils.py            # Utility function tests (10)
├── services/                    # Service layer tests (65 tests)
│   ├── test_authorization.py    # USPS API authorization (1)
│   ├── test_aws.py              # AWS operations (14)
│   ├── test_catdroool.py        # Core business logic (5)
│   ├── test_countries.py        # Country/state lookups (13)
│   ├── test_crypt.py            # Encryption operations (2)
│   ├── test_domestics.py        # Domestic shipping (2)
│   ├── test_dynamodb.py         # DynamoDB operations (7)
│   ├── test_emailer.py          # Email functionality (9)
│   └── test_trending.py         # Analytics/trending (8)
└── test_helpers/                # Test utilities
    └── test_helper.py           # Mock data and helpers
```

## Test Coverage by Module

### Service Layer

#### AWS (`test_aws.py`) - 14 tests
- Initialization and configuration
- Secrets Manager operations (get/put)
- DynamoDB resource management
- Error handling
- Singleton pattern behavior

#### DynamoDB (`test_dynamodb.py`) - 7 tests
- Item persistence (`put_item`)
- Query operations (`get_latest_customer_metrics`)
- Error handling for database failures
- Empty result handling

#### Email (`test_emailer.py`) - 9 tests
- SMTP connection and authentication
- Delivery and notification email types
- File attachment handling
- Error handling (SMTP failures, missing files)
- Email disabled mode

#### Trending (`test_trending.py`) - 8 tests
- Metrics building (domestic/international/total)
- Month-over-month comparison
- Excel report generation
- Handling missing historical data

#### Countries (`test_countries.py`) - 13 tests
- Database connection management
- Country name lookups by code
- State code/name lookups
- SQL file handling
- Error handling for database queries

#### Authorization (`test_authorization.py`) - 1 test
- USPS API token caching and retrieval

#### Crypt (`test_crypt.py`) - 2 tests
- Encryption key management
- Data encryption/decryption

#### Domestics (`test_domestics.py`) - 2 tests
- USPS address validation
- Address caching

#### Catdroool (`test_catdroool.py`) - 5 tests
- Mailing list sorting
- Field-based alphabetical ordering

### Common Utilities

#### Singleton (`test_singleton.py`) - 3 tests
- Single instance enforcement
- State sharing across instances
- Multiple singleton subclasses

#### Utils (`test_utils.py`) - 10 tests
- Time difference calculations
- Previous month calculations
- Shipment record population
- USPS address handling
- ZIP code validation

## Testing Patterns

### Mocking External Dependencies

All tests use mocks for external services to ensure:
- Fast test execution
- No external API calls
- Consistent test results
- No credentials required

Example mocked dependencies:
- AWS (boto3 client/resource)
- Stripe API
- PostgreSQL database
- SMTP servers
- USPS API

### Test Fixtures

Tests use pytest fixtures for common setup:
```python
@pytest.fixture
def mock_aws():
    mock = MagicMock()
    # Configure mock behavior
    return mock
```

### Singleton Testing

Services using the Singleton pattern require clearing instances:
```python
def test_example():
    # Clear singleton instances before test
    MyService._instances = {}
    # ... test code
```

## Writing New Tests

### Test File Naming
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.my_service import MyService


class TestMyService:
    def test_basic_functionality(self):
        """Test basic service functionality"""
        # Arrange
        service = MyService()
        
        # Act
        result = service.do_something()
        
        # Assert
        assert result == expected_value
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** describing what is being tested
3. **Mock external dependencies** completely
4. **Test both success and failure paths**
5. **Test edge cases** (empty inputs, None values, etc.)
6. **Use descriptive docstrings**

## Continuous Integration

Tests are automatically run on:
- Pull request creation
- Push to main branch
- Manual workflow dispatch

### CI Configuration

The test suite is configured to:
- Install dependencies
- Run all tests with verbose output
- Report coverage
- Fail on any test failure

## Troubleshooting

### Common Issues

**Import errors**
```bash
# Ensure dependencies are installed
pip install -r requirements.txt
```

**Singleton test failures**
```python
# Clear singleton instances before each test
MyService._instances = {}
```

**Mock not working**
```python
# Ensure correct patch path (use where it's imported, not where it's defined)
with patch("services.my_service.ExternalDep", return_value=mock):
    # test code
```

## Test Configuration

### pytest.ini (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
python_files = ["test*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure all tests pass
3. Add test documentation if introducing new patterns
4. Update this document if adding new test files

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
