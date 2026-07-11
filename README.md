# Catdroool Shipping Reports

Automated shipping report generation system for Catdroool subscription customers.

## Overview

This application generates shipping reports for Catdroool subscription customers by:
- Retrieving active subscriptions from Stripe
- Validating addresses via the Smarty US Street API
- Generating CSV reports for domestic and international customers
- Sending automated email reports
- Tracking customer metrics in DynamoDB

It runs once a month as a scheduled ECS Fargate task. See [Deployment](#deployment).

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

AWS credentials are resolved by boto3's default chain — your `~/.aws/credentials` profile
or `AWS_*` environment variables locally, and the ECS task role in Fargate. The application
never reads an access key from disk.

> **Careful:** `Catdroool.__init__` sends a startup notification email before it does any
> work, and the run ends by emailing the reports. A local run against production secrets
> will email real recipients. Set `EMAILS_ENABLED = False` in `src/config/config.py` first.

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
│       ├── aws.py           # AWS operations (Secrets, DynamoDB)
│       ├── catdroool.py     # Main business logic
│       ├── domestics.py     # Domestic shipping validation
│       ├── dynamodb.py      # DynamoDB operations
│       ├── emailer.py       # Email functionality
│       ├── s3.py            # Report archive
│       ├── stripeOps.py     # Stripe API operations
│       └── trending.py      # Analytics and metrics
├── tests/                   # Test suite (78 tests)
│   ├── common/              # Common utilities tests
│   ├── services/            # Service layer tests
│   └── test_helpers/        # Test utilities
├── infra/
│   └── catdroool-shipping.yaml  # CloudFormation: ECR, ECS, IAM, schedule
├── html/                    # Email templates
├── output/                  # Generated reports
├── cache/                   # Cached data
├── logs/                    # Application logs
├── Dockerfile              # Container image for the Fargate task
├── TESTING.md              # Testing documentation
├── Pipfile                 # Pipenv dependencies
└── pyproject.toml          # Project configuration
```

## Features

### Address Validation
- Smarty US Street API integration for domestic address validation
- Customers whose address cannot be matched are omitted from the report and flagged
- Partial matches are kept but flagged for review in Stripe

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

These are read from the environment so the same image can serve both stacks. The
CloudFormation task definition sets all four.

| Variable | Default | Effect |
|---|---|---|
| `APP_ENV` | `prod` | Selects `catdroool_customer_counts_{prod,dev}` in DynamoDB |
| `AWS_REGION` | `us-east-2` | Region for Secrets Manager and DynamoDB |
| `EMAILS_ENABLED` | `true` | When false, `send_email` returns immediately and no credentials are fetched |
| `ADDRESS_VALIDATION_ENABLED` | `true` | When false, no Smarty client is built and no lookup is ever spent |
| `REPORT_BUCKET` | `""` | S3 bucket for archived reports. Empty skips the upload |

The two flags accept `true/false`, `1/0`, `yes/no`, `on/off`, case-insensitively. **Anything
else raises at import.** A value silently read as false would ship unvalidated addresses to
production; one silently read as true would spend Smarty verifications. `bool("false")` is
`True`, so this is not a hypothetical.

## External Services

The application integrates with:
- **Stripe**: Customer and subscription data
- **Smarty US Street API**: Address validation
- **AWS Secrets Manager**: Secure credential storage
- **AWS DynamoDB**: Metrics tracking
- **AWS S3**: Report archive
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

## Deployment

The report runs as an ECS Fargate task in a **public subnet with a public IP and no inbound
rules**. It needs egress to Stripe, Smarty and Gmail; a public IP provides that for free,
whereas a private subnet would require a NAT Gateway at roughly $33/month to support twenty
minutes of work.

### AWS account

Everything deploys into the Catdroool account via the **`catdroool`** CLI profile. The justfile
passes `--profile` on every single AWS call, because without it they fall through to whatever
`default` happens to be, which is a *different account*. Confirm before you deploy anything:

```bash
just whoami
```

To make that a hard stop rather than a thing you have to remember to check, set
`expected_account` and any deploy will refuse to run if the profile resolves elsewhere:

```bash
just expected_account=<catdroool-account-id> deploy-dev
```

The three secrets the task role reads (`stripe_api_key`, `smarty_api_key`,
`catdroool_email_secrets`) and the DynamoDB trending tables already exist in that account and
are **not** created by the stack — which is another reason a deploy pointed at the wrong
account fails in confusing ways rather than obvious ones.

### First deploy

Create the stack with the schedule disabled, so nothing fires before an image exists:

```bash
just deploy-infra DISABLED
```

Build and push the image, then enable the schedule:

```bash
just push
just deploy-infra
```

The deploy recipes find the network themselves: the region's default VPC, and the subnets in
it whose route table reaches an Internet Gateway. Private subnets are skipped — the task has
a public IP and no NAT, so one would strand it on the image pull. Check what they resolved to
with `just network`, and pin them if the default VPC is not where this belongs:

```bash
just vpc_id=vpc-0abc123 subnet_ids=subnet-0aaa,subnet-0bbb deploy-infra
```

The three secrets the task role is granted (`stripe_api_key`, `smarty_api_key`,
`catdroool_email_secrets`) and the DynamoDB table are **not** created by the stack; they
already exist and are only referenced.

### Subsequent deploys

```bash
just push          # build, tag, push to ECR
```

The task definition points at the `latest` tag, so a push is enough. Run `just deploy-infra`
only when the template itself changes.

### Report archive

Every run uploads its four output files to `s3://catdroool-shipping-reports-<env>-<account>/<date>/`
before sending the email, so a failed send no longer means a lost report. The bucket is
private, encrypted, expires objects after a year, and is **retained if the stack is deleted**.

```bash
just reports                    # list what has been archived
just fetch-reports 2026-07-09   # pull one date into ./output/
```

### Testing a deployment without spending Smarty lookups

The Smarty allotment is capped monthly and one full run consumes several hundred
verifications, so a production run cannot be used as a test. Deploy a dev stack instead. It
exercises the real task role, the real egress rules, real Stripe (which is unmetered), and
the dev DynamoDB table — then writes the finished report to the dev bucket instead of
emailing it:

```bash
just deploy-dev
just app_env=dev push            # required: the dev stack gets its own, initially empty, ECR repo
just app_env=dev run-now
just app_env=dev logs
just app_env=dev reports         # the report is here, not in your inbox
```

**Every recipe after `deploy-dev` needs the `app_env=dev` prefix.** The justfile defaults
`app_env` to `prod`, and only `deploy-dev` overrides it internally — `push`, `run-now`, `logs`
and `reports` do not. So `just deploy-dev && just run-now` deploys dev and then runs
**production**, emailing the real recipients off a Smarty allotment that a single run half
consumes. The `push` step is not optional either: each stack has its own ECR repo
(`catdroool-shipping-${AppEnv}`), so a dev repo with no image fails with
`CannotPullContainerError`.

`deploy-dev` sets `EMAILS_ENABLED=false` and `ADDRESS_VALIDATION_ENABLED=false` and leaves
the schedule disabled. With validation off, `Domestics` never constructs a client and never
reads `smarty_api_key` — which also means a dev run cannot tell you whether the task role's
permission on that secret is correct. Verify that separately.

Addresses in a dev run pass through unverified from Stripe, so the CSVs are structurally
valid but not postally correct. Do not mail from them.

### Running it off-schedule

```bash
just run-now      # production: this emails the real recipients
```

### Watching a run

```bash
just logs
```

## Security

- Credentials stored in AWS Secrets Manager
- No secrets in source code or config files
- No long-lived access keys: the task assumes an IAM role scoped to three secrets and one
  DynamoDB table
- Rate limiting on API calls

## Troubleshooting

### Common Issues

**Missing AWS credentials**
```bash
# Confirm boto3 can resolve a caller. In Fargate this is the task role; locally it is
# whatever profile or AWS_* environment variables you have configured.
aws sts get-caller-identity
```

**Task dies immediately with "exec format error"**

The image architecture does not match the task definition. Building on Apple Silicon
produces `arm64`; pass `--platform linux/amd64` to `docker build` or set the stack's
`CpuArchitecture` parameter to `ARM64`.

**Smarty API errors**
```bash
# Verify Smarty credentials in AWS Secrets Manager
# Secret name: smarty_api_key, formatted as "<auth-id>:<auth-token>"
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
