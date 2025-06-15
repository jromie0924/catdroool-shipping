import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
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
    mock.get_key.return_value = "key"
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
    if os.path.exists("token_cache"):
        os.remove("token_cache")

@patch("services.authorization.Crypt")
@patch("services.authorization.Aws")
@patch("services.authorization.config", new=MockConfig)
def test_retrieve_credentials_with_valid_cache(mock_aws_class, mock_crypt_class, mock_crypt, mock_aws):
    mock_crypt_class.return_value = mock_crypt
    mock_aws_class.return_value = mock_aws
    with open("token_cache", "wb") as f:
        f.write(b"encrypted")
    auth = Authorization()
    assert auth._usps_api_token_cache["token"] == "abc"

@patch("services.authorization.Crypt")
@patch("services.authorization.Aws")
@patch("services.authorization.config", new=MockConfig)
def test_retrieve_credentials_with_expired_cache(mock_aws_class, mock_crypt_class, mock_crypt, mock_aws):
    # Expired token
    mock_crypt.decrypt_data.return_value = json.dumps({"expiration": 0, "token": "expired"})
    mock_crypt_class.return_value = mock_crypt
    mock_aws_class.return_value = mock_aws
    with open("token_cache", "wb") as f:
        f.write(b"encrypted")
    with patch("services.authorization.Authorization._fetch_new_token", return_value={"expiration": 9999999999999, "token": "new_token"}):
        auth = Authorization()
        assert auth._usps_api_token_cache["token"] == "new_token"

@patch("services.authorization.Crypt")
@patch("services.authorization.Aws")
@patch("services.authorization.config", new=MockConfig)
def test_retrieve_credentials_with_no_cache(mock_aws_class, mock_crypt_class, mock_crypt, mock_aws):
    mock_crypt_class.return_value = mock_crypt
    mock_aws_class.return_value = mock_aws
    if os.path.exists("token_cache"):
        os.remove("token_cache")
    with patch("services.authorization.Authorization._fetch_new_token", return_value={"expiration": 9999999999999, "token": "fresh_token"}):
        auth = Authorization()
        assert auth._usps_api_token_cache["token"] == "fresh_token"

@patch("services.authorization.Crypt")
@patch("services.authorization.Aws")
@patch("services.authorization.config", new=MockConfig)
def test_fetch_new_token_called_when_cache_invalid(mock_aws_class, mock_crypt_class, mock_crypt, mock_aws):
    mock_crypt.decrypt_data.side_effect = Exception("corrupt")
    mock_crypt_class.return_value = mock_crypt
    mock_aws_class.return_value = mock_aws
    with open("token_cache", "wb") as f:
        f.write(b"corrupt")
    with patch("services.authorization.Authorization._fetch_new_token", return_value={"expiration": 9999999999999, "token": "fallback_token"}) as fetch_mock:
        auth = Authorization()
        fetch_mock.assert_called_once()
        assert auth._usps_api_token_cache["token"] == "fallback_token"

@patch("services.authorization.Crypt")
@patch("services.authorization.Aws")
@patch("services.authorization.config", new=MockConfig)
def test_authorization_token_property(mock_aws_class, mock_crypt_class, mock_crypt, mock_aws):
    mock_crypt_class.return_value = mock_crypt
    mock_aws_class.return_value = mock_aws
    with open("token_cache", "wb") as f:
        f.write(b"encrypted")
    auth = Authorization()
    assert auth.token == "abc"