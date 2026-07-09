import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from requests.structures import CaseInsensitiveDict
from smartystreets_python_sdk import ClientBuilder, RequestsSender, StaticCredentials, exceptions as smarty_exceptions
from smartystreets_python_sdk.us_street import Lookup
from smartystreets_python_sdk.us_street.match_type import MatchType
from common.exceptions import AddressNotFoundError, CredentialsError, RateLimitError
from common.singleton import Singleton
from config import config
from services.aws import Aws


logger = logging.getLogger(config.APP_NAME)

# Smarty reports this in analysis.enhanced_match when it matched an address only by
# discarding part of what we sent it, e.g. a state that disagrees with the ZIP code.
IGNORED_INPUT = "ignored-input"

# Set on a returned address when Smarty ignored part of the input. The address is still
# usable, but the customer's Stripe record is suspect and worth a human look.
IGNORED_INPUT_KEY = "ignoredInput"

RETRY_AFTER_HEADER = "Retry-After"
DEFAULT_RETRY_AFTER_SECONDS = 60


class RetryAfterSender:
  """
  Sits directly beneath the SDK's RetrySender, which is what actually honors a 429 by
  sleeping for Retry-After and re-sending. RetrySender reads the header via
  Response.getHeader, which subscripts the header dict and then calls int() on the
  value. So a 429 that omits the header raises KeyError, and one carrying the HTTP-date
  form that RFC 9110 also permits raises ValueError -- in both cases before a single
  retry happens. Normalizing the header to integer seconds keeps that path on its feet.
  """

  def __init__(self, inner):
    self.inner = inner

  def send(self, request):
    response = self.inner.send(request)
    if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
      headers = CaseInsensitiveDict(response.headers or {})
      headers[RETRY_AFTER_HEADER] = str(self._retry_after_seconds(headers.get(RETRY_AFTER_HEADER)))
      response.headers = headers
    return response

  @staticmethod
  def _retry_after_seconds(value) -> int:
    try:
      return max(int(value), 0)
    except (TypeError, ValueError):
      pass

    try:
      delta = parsedate_to_datetime(value) - datetime.now(timezone.utc)
      return max(int(delta.total_seconds()), 0)
    except (TypeError, ValueError):
      logger.warning(f"Rate limited with an unusable {RETRY_AFTER_HEADER} header (got {value!r}). "
                     f"Backing off {DEFAULT_RETRY_AFTER_SECONDS}s instead.")
      return DEFAULT_RETRY_AFTER_SECONDS

class Domestics(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._aws = Aws()
    # Building the client reads the credentials out of AWS, so skip it entirely when
    # address validation is turned off.
    self._client = self._build_client() if config.ADDRESS_VALIDATION_ENABLED else None

  def _load_credentials(self) -> StaticCredentials:
    secret = self._aws.get_secret(key=config.SMARTY_API_KEY, type=str)
    if not secret:
      raise CredentialsError(f"Secret \"{config.SMARTY_API_KEY}\" was not found in AWS Secrets Manager.")

    api_key = json.loads(secret).get(config.SMARTY_API_KEY)
    auth_id, separator, auth_token = (api_key or "").partition(config.SMARTY_API_KEY_SEPARATOR)
    if not (separator and auth_id and auth_token):
      raise CredentialsError(f"Secret \"{config.SMARTY_API_KEY}\" is not in the expected "
                             f"\"<auth-id>{config.SMARTY_API_KEY_SEPARATOR}<auth-token>\" form.")

    return StaticCredentials(auth_id, auth_token)

  def _build_client(self):
    # with_sender swaps the innermost HTTP transport but leaves the rest of the SDK's
    # middleware, including RetrySender, wrapped around it.
    return ClientBuilder(self._load_credentials()) \
      .retry_at_most(config.SMARTY_MAX_RETRIES) \
      .with_licenses(config.SMARTY_LICENSES) \
      .with_sender(RetryAfterSender(RequestsSender())) \
      .build_us_street_api_client()

  def validate_address(self, address_1: str, address_2: str, city: str, state: str, zip: str) -> dict:
    # No client means validation was turned off when this was constructed.
    if self._client:
      params = {
        "street": address_1,
        "secondary": address_2 or "",
        "city": city,
        "state": state,
        "zipcode": zip
      }
      return self._validate_address(params=params)
    return {}

  def _validate_address(self, params: dict) -> dict:
    # ENHANCED is what populates analysis.enhanced_match, which is the only place Smarty
    # tells us it ignored part of the input rather than failing outright.
    lookup = Lookup(match=MatchType.ENHANCED, candidates=1, **params)

    try:
      self._client.send_lookup(lookup)
    except smarty_exceptions.TooManyRequestsError as e:
      raise RateLimitError() from e
    except smarty_exceptions.SmartyException as e:
      logger.error(f"Address validation failed: {e}")
      return {}

    if not lookup.result:
      raise AddressNotFoundError()

    candidate = lookup.result[0]
    address = self._to_address(candidate)

    if IGNORED_INPUT in (candidate.analysis.enhanced_match or ""):
      logger.warning(f"Smarty ignored part of the input when matching {candidate.delivery_line_1}.")
      address[IGNORED_INPUT_KEY] = True

    return address

  @staticmethod
  def _to_address(candidate) -> dict:
    # Rebuilt from components rather than delivery_line_1, which folds the secondary
    # address into the street line. Downstream keeps the two separate.
    components = candidate.components
    street_parts = [
      components.primary_number,
      components.street_predirection,
      components.street_name,
      components.street_suffix,
      components.street_postdirection
    ]
    secondary_parts = [components.secondary_designator, components.secondary_number]

    return {
      "streetAddress": " ".join(part for part in street_parts if part),
      "secondaryAddress": " ".join(part for part in secondary_parts if part),
      "city": components.city_name or "",
      "state": components.state_abbreviation or "",
      "ZIPCode": components.zipcode or "",
      "ZIPPlus4": components.plus4_code or "",
      "urbanization": components.urbanization or ""
    }
