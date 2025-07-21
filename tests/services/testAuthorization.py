import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.authorization import Authorization

class MockConfig:
  API_TOKEN_CACHE_FILE = "token_cache"
  APP_NAME = "test_app"
  USPS_CLIENT_ID = "client_id"
  USPS_CLIENT_SECRET = "client_secret"
  USPS_URI = "https://example.com"

@pytest.fixture
def mock_crypt():
  mock = MagicMock()
  mock.get_key.return_value = b"key"
  mock.decrypt_data.return_value = json.dumps({"expiration": 9999999999999, "token": "abc"})
  mock.encrypt_data.return_value = b"encrypted"
  return mock

@pytest.fixture
def mock_aws():
  mock = MagicMock()
  mock.secrets_client.get_secret_value.return_value = {
    "SecretString": json.dumps({"client_id": "id", "client_secret": "secret"})
  }
  return mock

@pytest.fixture(autouse=True)
def cleanup_token_cache():
  yield
  try:
    os.remove("token_cache")
  except FileNotFoundError:
    pass

def test_retrieve_credentials_with_valid_cache(mock_crypt, mock_aws):
  with patch("services.authorization.Crypt", return_value=mock_crypt), \
     patch("services.authorization.Aws", return_value=mock_aws), \
     patch("services.authorization.config", MockConfig):

    # Write a valid cache file
    with open("token_cache", "wb") as f:
      f.write(b"encrypted")

    auth = Authorization()
    assert auth._usps_api_token_cache["token"] == "abc"
