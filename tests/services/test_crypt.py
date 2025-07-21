import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.crypt import Crypt

class MockConfig:
  CRYPT_SECRET_NAME = "secret_name"

@pytest.fixture
def mock_aws():
  class MockAWS:
    def get_secret(self, **kwargs):
      return b"key"
    def put_secret(self, **kwargs):
      return None
  return MockAWS()

@pytest.fixture
def mock_fernet():
  class MockFernet:
    def __init__(self, key):
      self.key = key
    def encrypt(self, data):
      return b"encrypted_" + data
    def decrypt(self, token):
      return b"decrypted_" + token
    @staticmethod
    def generate_key():
      return b"key"
  return MockFernet

def test_init_loads_key_from_aws(monkeypatch, mock_aws, mock_fernet):
  monkeypatch.setattr("services.crypt.Aws", lambda: mock_aws)
  monkeypatch.setattr("services.crypt.Fernet", mock_fernet)
  crypt = Crypt()
  assert crypt.get_key() == b"key"

def test_encrypt_decrypt(monkeypatch, mock_aws, mock_fernet):
  monkeypatch.setattr("services.crypt.Aws", lambda: mock_aws)
  monkeypatch.setattr("services.crypt.Fernet", mock_fernet)
  crypt = Crypt()
  data = "mydata"
  key = b'key'
  encrypted = crypt.encrypt_data(key=key, data=data)
  assert encrypted == b"encrypted_mydata"
  decrypted = crypt.decrypt_data(data=encrypted, key=key)
  assert decrypted == "decrypted_encrypted_mydata"
