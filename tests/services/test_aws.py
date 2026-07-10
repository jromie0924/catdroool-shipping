import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.aws import Aws


class MockConfig:
  AWS_REGION = "us-east-1"
  APP_NAME = "test_app"


@pytest.fixture
def mock_config():
  return MockConfig


@pytest.fixture(autouse=True)
def clear_singleton():
  Aws._instances = {}
  yield
  Aws._instances = {}


@pytest.fixture
def mock_boto3_client():
  mock = MagicMock()
  mock.get_secret_value.return_value = {
    "SecretString": "test_secret_string",
    "SecretBinary": b"test_secret_binary"
  }
  mock.create_secret.return_value = {"ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"}
  return mock


def test_aws_init_success(mock_config):
  """Test AWS initialization picks up the configured region"""
  with patch("services.aws.config", mock_config):
    aws = Aws()

    assert aws._region == "us-east-1"


def test_aws_secrets_client_property(mock_config):
  """Test secrets_client property builds a boto3 client without explicit credentials"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client") as mock_boto_client:

    aws = Aws()
    aws.secrets_client

    # No aws_access_key_id / aws_secret_access_key: boto3 resolves the task role itself.
    mock_boto_client.assert_called_once_with(
      'secretsmanager',
      region_name="us-east-1"
    )


def test_aws_dynamodb_resource_property(mock_config):
  """Test dynamodb_resource property builds a boto3 resource without explicit credentials"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.resource") as mock_boto_resource:

    aws = Aws()
    aws.dynamodb_resource

    mock_boto_resource.assert_called_once_with(
      'dynamodb',
      region_name="us-east-1"
    )


def test_aws_s3_client_property(mock_config):
  """Test s3_client property builds a boto3 client without explicit credentials"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client") as mock_boto_client:

    aws = Aws()
    aws.s3_client

    mock_boto_client.assert_called_once_with(
      's3',
      region_name="us-east-1"
    )


def test_get_secret_string(mock_config, mock_boto3_client):
  """Test getting a string secret from AWS"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_boto3_client):

    aws = Aws()
    result = aws.get_secret("test_key", str)

    assert result == "test_secret_string"
    mock_boto3_client.get_secret_value.assert_called_once_with(SecretId="test_key")


def test_get_secret_binary(mock_config, mock_boto3_client):
  """Test getting a binary secret from AWS"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_boto3_client):

    aws = Aws()
    result = aws.get_secret("test_key", bytes)

    assert result == b"test_secret_binary"


def test_get_secret_exception(mock_config):
  """Test get_secret handles exceptions gracefully"""
  mock_client = MagicMock()
  mock_client.get_secret_value.side_effect = Exception("AWS Error")

  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_client):

    aws = Aws()
    result = aws.get_secret("test_key", str)

    # Should return None on exception
    assert result is None


def test_put_secret_string(mock_config, mock_boto3_client):
  """Test putting a string secret to AWS"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_boto3_client):

    aws = Aws()
    aws.put_secret("test_key", "test_value", str)

    mock_boto3_client.create_secret.assert_called_once_with(
      Name="test_key",
      SecretString="test_value"
    )


def test_put_secret_binary(mock_config, mock_boto3_client):
  """Test putting a binary secret to AWS"""
  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_boto3_client):

    aws = Aws()
    aws.put_secret("test_key", b"test_value", bytes)

    mock_boto3_client.create_secret.assert_called_once_with(
      Name="test_key",
      SecretBinary=b"test_value"
    )


def test_put_secret_exception(mock_config):
  """Test put_secret handles exceptions gracefully"""
  mock_client = MagicMock()
  mock_client.create_secret.side_effect = Exception("AWS Error")

  with patch("services.aws.config", mock_config), \
       patch("boto3.client", return_value=mock_client):

    aws = Aws()
    # Should not raise exception
    aws.put_secret("test_key", "test_value", str)


def test_aws_singleton_behavior(mock_config):
  """Test that Aws follows singleton pattern"""
  with patch("services.aws.config", mock_config):
    aws1 = Aws()
    aws2 = Aws()

    assert aws1 is aws2
