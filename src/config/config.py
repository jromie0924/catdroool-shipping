ENV = "prod"

APP_NAME = "catdroool_shipping_reports"
LOGGING_LEVEL = "INFO"
LOG_FILE_LOCATION = "logs"
EMAILS_ENABLED = True
ADDRESS_VALIDATION_ENABLED = True

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
AWS_ACCESS_KEY_FILENAME = "catdroool_app_user_accessKeys.csv"
AWS_REGION = "us-east-2"
AWS_ACCESS_KEY_ID_NAME = 'Access key ID'
AWS_SECRET_ACCESS_KEY_NAME = 'Secret access key'

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
