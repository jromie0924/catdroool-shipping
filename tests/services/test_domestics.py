import json
import os
import pytest
import sys

from common.exceptions import AddressNotFoundError, CredentialsError, RateLimitError
from common.singleton import Singleton
from config import config
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from requests.structures import CaseInsensitiveDict
from services.domestics import DEFAULT_RETRY_AFTER_SECONDS, Domestics, IGNORED_INPUT_KEY, RetryAfterSender
from smartystreets_python_sdk import Response, exceptions as smarty_exceptions
from smartystreets_python_sdk.us_street import Candidate
from smartystreets_python_sdk.us_street.match_type import MatchType
from unittest.mock import patch, MagicMock

from tests.test_helpers import test_helper

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

@pytest.fixture(autouse=True)
def reset_singleton():
  # Domestics is a Singleton, so without this each test would reuse the first
  # test's instance and its mocked Smarty client.
  Singleton._instances = {}
  yield
  Singleton._instances = {}

def secret_string(value):
  return json.dumps({config.SMARTY_API_KEY: value})

@pytest.fixture
def mock_aws():
  mock = MagicMock()
  mock.get_secret.return_value = secret_string("test-auth-id:test-auth-token")
  return mock

@pytest.fixture
def domestics_and_client(mock_aws):
  with patch("services.domestics.Aws", return_value=mock_aws), \
    patch("services.domestics.ClientBuilder") as mock_builder:
      client = MagicMock()
      mock_builder.return_value \
        .retry_at_most.return_value \
        .with_licenses.return_value \
        .with_sender.return_value \
        .build_us_street_api_client.return_value = client
      yield Domestics(), client

def build_domestics(mock_aws):
  with patch("services.domestics.Aws", return_value=mock_aws), \
    patch("services.domestics.ClientBuilder") as mock_builder:
      return Domestics(), mock_builder

def returns_candidate(payload):
  """Mimic send_lookup, which writes its results onto the Lookup it is handed."""
  return lambda lookup: lookup.result.append(Candidate(payload))


def test_validate_address_returns_mapped_address(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate)
  actual_address = domestics.validate_address(address_1="4567 other street",
                                              address_2="",
                                              city="San Francisco",
                                              state="CA",
                                              zip="94102")
  assert actual_address == test_helper.mock_smarty_validated_address
  client.send_lookup.assert_called_once()

def test_validate_address_sends_expected_lookup(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate)
  domestics.validate_address(address_1="4567 other street",
                             address_2="Apt 2",
                             city="San Francisco",
                             state="CA",
                             zip="94102")
  lookup = client.send_lookup.call_args.args[0]
  assert lookup.street == "4567 other street"
  assert lookup.secondary == "Apt 2"
  assert lookup.city == "San Francisco"
  assert lookup.state == "CA"
  assert lookup.zipcode == "94102"

def test_validate_address_looks_up_every_time(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate)
  args = dict(address_1="4567 other street", address_2="", city="San Francisco", state="CA", zip="94102")
  first = domestics.validate_address(**args)
  second = domestics.validate_address(**args)
  assert first == second
  assert client.send_lookup.call_count == 2

def test_validate_address_keeps_secondary_address_separate(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate_with_secondary)
  actual_address = domestics.validate_address(address_1="809 S Lamar Blvd",
                                              address_2="Apt 214",
                                              city="Austin",
                                              state="TX",
                                              zip="78704")
  assert actual_address["streetAddress"] == "809 S Lamar Blvd"
  assert actual_address["secondaryAddress"] == "Apt 214"
  assert actual_address["ZIPPlus4"] == "1565"

def test_validate_address_no_candidates_raises(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = lambda lookup: None
  with pytest.raises(AddressNotFoundError):
    domestics.validate_address(address_1="nowhere",
                               address_2="",
                               city="Nowhere",
                               state="ZZ",
                               zip="00000")

def test_validate_address_ignored_input_is_flagged_but_accepted(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate_ignored_input)
  actual_address = domestics.validate_address(address_1="809 S Lamar Blvd",
                                              address_2="Apt 214",
                                              city="Austin",
                                              state="DE",
                                              zip="78704")
  assert actual_address[IGNORED_INPUT_KEY] is True
  assert actual_address["streetAddress"] == "809 S Lamar Blvd"
  assert actual_address["state"] == "TX"

def test_validate_address_clean_match_is_not_flagged(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate)
  actual_address = domestics.validate_address(address_1="4567 other street",
                                              address_2="",
                                              city="San Francisco",
                                              state="CA",
                                              zip="94102")
  assert IGNORED_INPUT_KEY not in actual_address

def test_validate_address_uses_enhanced_match(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = returns_candidate(test_helper.mock_smarty_candidate)
  domestics.validate_address(address_1="4567 other street",
                             address_2="",
                             city="San Francisco",
                             state="CA",
                             zip="94102")
  lookup = client.send_lookup.call_args.args[0]
  assert lookup.match == MatchType.ENHANCED

def test_validate_address_rate_limited_raises(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = smarty_exceptions.TooManyRequestsError("429")
  with pytest.raises(RateLimitError):
    domestics.validate_address(address_1="4567 other street",
                               address_2="",
                               city="San Francisco",
                               state="CA",
                               zip="94102")

def test_validate_address_smarty_error_returns_empty(domestics_and_client):
  domestics, client = domestics_and_client
  client.send_lookup.side_effect = smarty_exceptions.BadCredentialsError("nope")
  actual_address = domestics.validate_address(address_1="4567 other street",
                                              address_2="",
                                              city="San Francisco",
                                              state="CA",
                                              zip="94102")
  assert actual_address == {}

def test_credentials_are_read_from_aws_secret(mock_aws):
  _, mock_builder = build_domestics(mock_aws)
  mock_aws.get_secret.assert_called_once_with(key=config.SMARTY_API_KEY, type=str)
  credentials = mock_builder.call_args.args[0]
  assert credentials.auth_id == "test-auth-id"
  assert credentials.auth_token == "test-auth-token"

def test_credentials_split_on_first_separator_only(mock_aws):
  # An auth token that itself contains a colon must survive intact.
  mock_aws.get_secret.return_value = secret_string("the-id:tok:en")
  _, mock_builder = build_domestics(mock_aws)
  credentials = mock_builder.call_args.args[0]
  assert credentials.auth_id == "the-id"
  assert credentials.auth_token == "tok:en"

def test_credentials_missing_secret_raises(mock_aws):
  # Aws.get_secret logs and returns None when the secret cannot be read.
  mock_aws.get_secret.return_value = None
  with pytest.raises(CredentialsError):
    build_domestics(mock_aws)

def test_credentials_missing_key_in_secret_raises(mock_aws):
  mock_aws.get_secret.return_value = json.dumps({"some_other_key": "id:token"})
  with pytest.raises(CredentialsError):
    build_domestics(mock_aws)

def test_credentials_without_separator_raises(mock_aws):
  mock_aws.get_secret.return_value = secret_string("no-separator-here")
  with pytest.raises(CredentialsError):
    build_domestics(mock_aws)

def test_credentials_with_empty_half_raises(mock_aws):
  mock_aws.get_secret.return_value = secret_string("only-an-id:")
  with pytest.raises(CredentialsError):
    build_domestics(mock_aws)

def test_credentials_not_fetched_when_validation_disabled(mock_aws):
  with patch("services.domestics.config.ADDRESS_VALIDATION_ENABLED", False):
    domestics, _ = build_domestics(mock_aws)
  mock_aws.get_secret.assert_not_called()
  assert domestics.validate_address(address_1="a", address_2="", city="b", state="c", zip="d") == {}


class StubSender:
  def __init__(self, response):
    self.response = response

  def send(self, request):
    return self.response


def send_through_retry_after_sender(status_code, headers):
  response = Response(payload="", status_code=status_code, headers=CaseInsensitiveDict(headers))
  return RetryAfterSender(StubSender(response)).send(request=None)


def test_retry_after_sender_passes_through_seconds():
  response = send_through_retry_after_sender(429, {"Retry-After": "7"})
  assert response.getHeader("Retry-After") == "7"

def test_retry_after_sender_is_case_insensitive():
  response = send_through_retry_after_sender(429, {"retry-after": "5"})
  assert response.getHeader("Retry-After") == "5"

def test_retry_after_sender_defaults_when_header_missing():
  # The SDK's RetrySender subscripts this header, so a 429 without it would raise KeyError.
  response = send_through_retry_after_sender(429, {})
  assert response.getHeader("Retry-After") == str(DEFAULT_RETRY_AFTER_SECONDS)

def test_retry_after_sender_defaults_when_header_unparseable():
  response = send_through_retry_after_sender(429, {"Retry-After": "soon"})
  assert response.getHeader("Retry-After") == str(DEFAULT_RETRY_AFTER_SECONDS)

def test_retry_after_sender_converts_http_date_to_seconds():
  future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=45))
  response = send_through_retry_after_sender(429, {"Retry-After": future})
  assert 40 <= int(response.getHeader("Retry-After")) <= 45

def test_retry_after_sender_clamps_negative_seconds():
  response = send_through_retry_after_sender(429, {"Retry-After": "-9"})
  assert response.getHeader("Retry-After") == "0"

def test_retry_after_sender_leaves_non_429_untouched():
  response = Response(payload="", status_code=200, headers=None)
  assert RetryAfterSender(StubSender(response)).send(request=None).headers is None


def test_validate_address_disabled_does_not_call_smarty(mock_aws):
  with patch("services.domestics.config.ADDRESS_VALIDATION_ENABLED", False), \
    patch("services.domestics.Aws", return_value=mock_aws), \
    patch("services.domestics.ClientBuilder") as mock_builder:
      domestics = Domestics()
  assert domestics.validate_address(address_1="4567 other street",
                                    address_2="",
                                    city="San Francisco",
                                    state="CA",
                                    zip="94102") == {}
  mock_builder.assert_not_called()
