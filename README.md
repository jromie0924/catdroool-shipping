# Catdroool Shipping Reports

Automated shipping report generation system for Catdroool subscription customers.

## Overview

This application generates shipping reports for Catdroool subscription customers by:
- Retrieving active subscriptions from Stripe
- Validating addresses via USPS API
- Generating CSV reports for domestic and international customers
- Sending automated email reports
- Tracking customer metrics in DynamoDB

## Quick Start

### Installation

```bash
# Install dependencies using pipenv (recommended)
pipenv install
pipenv shell

# Or using pip
pip install -r requirements.txt
```

### Running the Application

```bash
# Run the main application
python src/app.py
```

### Running Tests

```bash
# Run all tests
just test

# Or using pytest directly
python -m pytest tests/ -v
```

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

## Project Structure

```
catdroool-shipping/
├── src/
│   ├── common/              # Shared utilities
│   │   ├── singleton.py     # Singleton pattern base class
│   │   └── utils.py         # Utility functions
│   ├── config/
│   │   └── config.py        # Application configuration
│   ├── models/              # Data models
│   │   ├── emailType.py     # Email type enum
│   │   └── error.py         # Error collection
│   └── services/            # Business logic services
│       ├── authorization.py # USPS API authentication
│       ├── aws.py           # AWS operations (Secrets, DynamoDB)
│       ├── catdroool.py     # Main business logic
│       ├── countries.py     # Country/state lookups
│       ├── crypt.py         # Encryption services
│       ├── domestics.py     # Domestic shipping validation
│       ├── dynamodb.py      # DynamoDB operations
│       ├── emailer.py       # Email functionality
│       ├── stripeOps.py     # Stripe API operations
│       └── trending.py      # Analytics and metrics
├── tests/                   # Test suite (75 tests)
│   ├── common/              # Common utilities tests
│   ├── services/            # Service layer tests
│   └── test_helpers/        # Test utilities
├── html/                    # Email templates
├── sql/                     # SQL queries
├── output/                  # Generated reports
├── cache/                   # Cached data
├── logs/                    # Application logs
├── TESTING.md              # Testing documentation
├── Pipfile                 # Pipenv dependencies
└── pyproject.toml          # Project configuration
```

## Features

### Address Validation
- USPS API integration for domestic address validation
- Address caching to reduce API calls
- Fallback to Stripe address if validation fails

### Report Generation
- Domestic customer CSV reports
- International customer CSV reports
- Error tracking CSV reports
- Customer metrics Excel workbook

### Email Delivery
- Automated email delivery with attachments
- Startup notifications
- Configurable recipients for different email types

### Analytics
- Month-over-month customer count tracking
- Domestic vs. international metrics
- Historical trend analysis stored in DynamoDB

## Configuration

Key configuration values in `src/config/config.py`:

```python
# Environment
ENV = "prod"  # or "dev"

# Feature flags
EMAILS_ENABLED = True
ADDRESS_VALIDATION_ENABLED = True

# Product filters
PRODUCT_FILTER = "Catdroool Club"
INTERNATIONAL_FILTER = "International"
```

## External Services

The application integrates with:
- **Stripe**: Customer and subscription data
- **USPS API**: Address validation
- **AWS Secrets Manager**: Secure credential storage
- **AWS DynamoDB**: Metrics tracking
- **PostgreSQL**: Country/state database
- **Gmail SMTP**: Email delivery

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Document functions with docstrings

### Testing

- Write unit tests for new features
- All tests must pass before merging
- Use mocks for external dependencies
- See [TESTING.md](TESTING.md) for details

### Building

```bash
# Install and test
just build

# Just install
just install

# Just test
just test
```

## Security

- Credentials stored in AWS Secrets Manager
- Encryption for cached sensitive data
- No secrets in source code or config files
- Rate limiting on API calls

## Troubleshooting

### Common Issues

**Missing AWS credentials**
```bash
# Ensure AWS credentials file exists
ls system_files/catdroool_app_user_accessKeys.csv
```

**Database connection errors**
```bash
# Check database secret in AWS Secrets Manager
# Secret name: world_database_connection
```

**USPS API errors**
```bash
# Verify USPS credentials in AWS Secrets Manager
# Check API token cache: cache/api_tokens.bin
```

## Contributing

1. Create a feature branch
2. Write tests for new functionality
3. Ensure all tests pass
4. Submit a pull request

## License

Proprietary - Catdroool Internal Use Only

## Support

For questions or issues, contact the development team.
