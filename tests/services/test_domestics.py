import json
import os
import pytest
import sys

from services.domestics import Domestics
from unittest import mock
from unittest.mock import patch, MagicMock

from tests.test_helpers import test_helper

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

mock_filepath = "mock/path"

class MockConfig:
  VALIDATED_ADDRESSES_CACHE_FILE = mock_filepath
  ADDRESS_VALIDATION_ENABLED = True
  
@pytest.fixture
def mock_crypt():
  mock = MagicMock()
  mock.get_key.return_value = b"key"
  mock.encrypt_data.return_value = b"encrypted"
  cached_data = test_helper.mock_cached_address
  mock.decrypt_data.return_value = json.dumps(cached_data)
  return mock

@pytest.fixture
def mock_authorization():
  mock = MagicMock()
  mock.usps_token.return_value = "token"
  return mock


def test_validate_address_address_cached(mock_crypt, mock_authorization):
  with patch("services.domestics.Crypt", return_value=mock_crypt), \
    patch("services.domestics.Authorization", return_value=mock_authorization), \
      patch("builtins.open", new_callable=mock.mock_open, read_data=b"data"):
        domestics = Domestics()
        actual_address = domestics.validate_address(address_1="1234 main street",
                                                    address_2="",
                                                    city="Chicago",
                                                    state="IL",
                                                    zip="60601")
        assert actual_address == json.loads(list(test_helper.mock_cached_address.values())[0])

def test_validate_address_address_not_cached(mock_crypt, mock_authorization):
  with patch("services.domestics.Crypt", return_value=mock_crypt), \
    patch("services.domestics.Authorization", return_value=mock_authorization), \
    patch("builtins.open", new_callable=mock.mock_open, read_data=b"data"), \
    patch("requests.request") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"address": test_helper.mock_retrieved_usps_address}
        domestics = Domestics()
        actual_address = domestics.validate_address(address_1="4567 other street",
                                                    address_2="",
                                                    city="San Francisco",
                                                    state="CA",
                                                    zip="94102")
        assert actual_address == json.loads(list(test_helper.mock_cached_address.values())[0])