# import unittest
# import json
# import sys
# import os
# from unittest.mock import patch, MagicMock, mock_open

# # Add the src directory to the Python path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# from services.authorization import Authorization

# class TestAuthorization(unittest.TestCase):

#     def setUp(self):
#         class MockConfig:
#             API_TOKEN_CACHE_FILE = "token_cache"
#             APP_NAME = "test_app"
#             USPS_CLIENT_ID = "client_id"
#             USPS_CLIENT_SECRET = "client_secret"
#             USPS_URI = "https://example.com"
#         self.mock_config = MockConfig

#         self.mock_crypt = MagicMock()
#         self.mock_crypt.get_key.return_value = "key"
#         self.mock_crypt.decrypt_data.return_value = json.dumps({"expiration": 9999999999999, "token": "abc"})
#         self.mock_crypt.encrypt_data.return_value = b"encrypted"

#         self.mock_aws = MagicMock()
#         self.mock_aws.secrets_client.get_secret_value.return_value = {
#             "SecretString": json.dumps({"client_id": "id", "client_secret": "secret"})
#         }

#     @patch("services.authorization.Crypt")
#     @patch("services.authorization.Aws")
#     @patch("services.authorization.config")
#     def test_retrieve_credentials_with_valid_cache(self, mock_config_class, mock_aws_class, mock_crypt_class):
#         mock_config_class.API_TOKEN_CACHE_FILE = "token_cache"
#         mock_crypt_class.return_value = self.mock_crypt
#         mock_aws_class.return_value = self.mock_aws

#         # Write a valid cache file
#         with open("token_cache", "wb") as f:
#             f.write(b"encrypted")

#         with patch("services.authorization.config", self.mock_config):
#             auth = Authorization()
#             self.assertEqual(auth._usps_api_token_cache["token"], "abc")


# if __name__ == "__main__":
#     unittest.main()

