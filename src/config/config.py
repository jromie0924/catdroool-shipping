import os

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _env_flag(name: str, default: bool) -> bool:
  """
  Read a boolean feature flag from the environment.

  Anything unrecognized raises rather than defaulting. Guessing in either direction is
  expensive: a value silently read as false disables address validation in production and
  ships unverified addresses, and one silently read as true spends Smarty lookups out of a
  capped monthly allotment. bool("false") is True, so this cannot be done inline.
  """
  raw = os.environ.get(name)
  if raw is None:
    return default

  value = raw.strip().lower()
  if value in _TRUE_VALUES:
    return True
  if value in _FALSE_VALUES:
    return False

  raise ValueError(f"{name} must be one of {sorted(_TRUE_VALUES | _FALSE_VALUES)}, got {raw!r}")


ENV = os.environ.get("APP_ENV", "prod")

APP_NAME = "catdroool_shipping_reports"
LOGGING_LEVEL = "INFO"
LOG_FILE_LOCATION = "logs"

# Both default on, so an unconfigured environment behaves like production. A dev stack turns
# them off to exercise the full deployment without emailing anyone or spending a Smarty
# lookup; with validation off, Domestics never builds a client and never reads the secret.
EMAILS_ENABLED = _env_flag("EMAILS_ENABLED", True)
ADDRESS_VALIDATION_ENABLED = _env_flag("ADDRESS_VALIDATION_ENABLED", True)

PRODUCT_FILTER = "Catdroool Club"
INTERNATIONAL_FILTER = "International"
DATE_FORMAT_STRING = "%Y-%m-%d"
DATETIME_FORMAT_STRING = "%Y-%m-%dT%H:%M:%S"
TIMESTAMP = 'timestamp'
SORT_FIELD = "ShippingAddressCity"

CACHE_TIMEOUT = 24 # hours

# Stripe
STRIPE_SECRET_KEY = 'stripe_api_key'
STRIPE_CALLS_PER_SECOND = 100
STRIPE_SECONDS = 1

# AWS Constants
# ECS does not inject a region into the container, so the task definition sets AWS_REGION
# explicitly. The default keeps local runs pointed at the same account.
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# S3
# Where the generated reports are archived. Empty means "don't upload", which is the right
# behaviour for a local run. On a dev stack this is the only place the report survives,
# since emails are turned off and the task's disk is ephemeral.
REPORT_BUCKET = os.environ.get("REPORT_BUCKET", "")

# Smarty
SMARTY_API_KEY = 'smarty_api_key' # both the AWS secret name and the key within it
SMARTY_API_KEY_SEPARATOR = ':' # the secret holds "<auth-id>:<auth-token>"
SMARTY_LICENSES = ["us-core-cloud"]
SMARTY_MAX_RETRIES = 5 # the SDK sleeps for the Retry-After value on a 429 and retries this many times

# Email
DELIVERY_EMAIL_SUBJECT = "Catdroool Shipping File Delivery"
NOTIFICATION_EMAIL_SUBJECT = "Catdroool Shipping Startup Notification"

#DynamoDB
CATDROOOL_TRENDING_DYNAMO_PARTITION_KEY="month"
CATDROOOL_TRENDING_DYNAMODB_TABLE = "catdroool_customer_counts_prod" if ENV == "prod" else "catdroool_customer_counts_dev"
