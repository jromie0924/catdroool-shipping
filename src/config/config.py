APP_NAME = "catdroool_shipping_reports"
LOGGING_LEVEL = "INFO"
LOG_FILE_LOCATION = "logs"
API_TOKEN_CACHE_FILE = 'cache/api_tokens.bin'
EMAILS_ENABLED = True

PRODUCT_FILTER = "Catdroool Club"
INTERNATIONAL_FILTER = "International"
DATE_FORMAT_STRING = "%Y-%m-%d"
DATETIME_FORMAT_STRING = "%Y-%m-%dT%H:%M:%S"
TIMESTAMP = 'timestamp'

CACHE_TIMEOUT = 24 # hours

# Stripe
STRIPE_SECRET_KEY = 'stripe_api_key'

# AWS Constants
AWS_ACCESS_KEY_FILENAME = "catdroool_app_user_accessKeys.csv"
AWS_REGION = "us-east-2"
AWS_ACCESS_KEY_ID_NAME = 'Access key ID'
AWS_SECRET_ACCESS_KEY_NAME = 'Secret access key'
AWS_DB_SECRET_NAME = 'world_database_connection'

# USPS
USPS_CLIENT_ID = "client_id"
USPS_CLIENT_SECRET = "client_secret"
USPS_URI = "https://apis.usps.com"

# Crypt
CRYPT_SECRET_NAME = "crypt_key"
CRYPT_TTL_DAYS = 90

# Database
DATABASE_SERVER = 'tolfmachine'
DATABASE_NAME = 'world'

# Email
DELIVERY_EMAIL_SUBJECT = "Catdroool Shipping File Delivery"
NOTIFICATION_EMAIL_SUBJECT = "Catdroool Shipping Startup Notification"