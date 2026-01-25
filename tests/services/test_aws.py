import json
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.aws import Aws


class MockConfig:
  AWS_REGION = "us-east-1"
  AWS_ACCESS_KEY_FILENAME = "test_credentials.csv"
  AWS_ACCESS_KEY_ID_NAME = "Access key ID"
  AWS_SECRET_ACCESS_KEY_NAME = "Secret access key"
  APP_NAME = "test_app"


@pytest.fixture
def mock_config():
  return MockConfig


@pytest.fixture
def valid_csv_data():
  return "Access key ID,Secret access key\nAKIATESTKEY123,test_secret_key_456"


@pytest.fixture
def mock_boto3_client():
  mock = MagicMock()
  mock.get_secret_value.return_value = {
    "SecretString": "test_secret_string",
    "SecretBinary": b"test_secret_binary"
  }
  mock.create_secret.return_value = {"ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:test"}
  return mock


@pytest.fixture
def mock_boto3_resource():
  return MagicMock()


def test_aws_init_success(valid_csv_data, mock_config):
  """Test AWS initialization with valid credentials file"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)):
    aws = Aws(aws_secret_loc="/test/path")
    
    assert aws._region == "us-east-1"
    assert aws._access_key == "AKIATESTKEY123"
    assert aws._secret_key == "test_secret_key_456"


def test_aws_init_file_not_found(mock_config):
  """Test AWS initialization when credentials file is not found"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", side_effect=FileNotFoundError):
    with pytest.raises(FileNotFoundError):
      Aws(aws_secret_loc="/invalid/path")


def test_aws_secrets_client_property(valid_csv_data, mock_config):
  """Test secrets_client property returns boto3 client"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client") as mock_boto_client:
    
    aws = Aws(aws_secret_loc="/test/path")
    client = aws.secrets_client
    
    mock_boto_client.assert_called_once_with(
      'secretsmanager',
      aws_access_key_id="AKIATESTKEY123",
      aws_secret_access_key="test_secret_key_456",
      region_name="us-east-1"
    )


def test_aws_dynamodb_resource_property(valid_csv_data, mock_config):
  """Test dynamodb_resource property returns boto3 resource"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.resource") as mock_boto_resource:
    
    aws = Aws(aws_secret_loc="/test/path")
    resource = aws.dynamodb_resource
    
    mock_boto_resource.assert_called_once_with(
      'dynamodb',
      aws_access_key_id="AKIATESTKEY123",
      aws_secret_access_key="test_secret_key_456",
      region_name="us-east-1"
    )


def test_get_secret_string(valid_csv_data, mock_config, mock_boto3_client):
  """Test getting a string secret from AWS"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_boto3_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    result = aws.get_secret("test_key", str)
    
    assert result == "test_secret_string"
    mock_boto3_client.get_secret_value.assert_called_once_with(SecretId="test_key")


def test_get_secret_binary(valid_csv_data, mock_config, mock_boto3_client):
  """Test getting a binary secret from AWS"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_boto3_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    result = aws.get_secret("test_key", bytes)
    
    assert result == b"test_secret_binary"


def test_get_secret_exception(valid_csv_data, mock_config):
  """Test get_secret handles exceptions gracefully"""
  # Clear singleton instances
  Aws._instances = {}
  
  mock_client = MagicMock()
  mock_client.get_secret_value.side_effect = Exception("AWS Error")
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    result = aws.get_secret("test_key", str)
    
    # Should return None on exception
    assert result is None


def test_put_secret_string(valid_csv_data, mock_config, mock_boto3_client):
  """Test putting a string secret to AWS"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_boto3_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    aws.put_secret("test_key", "test_value", str)
    
    mock_boto3_client.create_secret.assert_called_once_with(
      Name="test_key",
      SecretString="test_value"
    )


def test_put_secret_binary(valid_csv_data, mock_config, mock_boto3_client):
  """Test putting a binary secret to AWS"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_boto3_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    aws.put_secret("test_key", b"test_value", bytes)
    
    mock_boto3_client.create_secret.assert_called_once_with(
      Name="test_key",
      SecretBinary=b"test_value"
    )


def test_put_secret_exception(valid_csv_data, mock_config):
  """Test put_secret handles exceptions gracefully"""
  # Clear singleton instances
  Aws._instances = {}
  
  mock_client = MagicMock()
  mock_client.create_secret.side_effect = Exception("AWS Error")
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)), \
       patch("boto3.client", return_value=mock_client):
    
    aws = Aws(aws_secret_loc="/test/path")
    # Should not raise exception
    aws.put_secret("test_key", "test_value", str)


def test_aws_singleton_behavior(valid_csv_data, mock_config):
  """Test that Aws follows singleton pattern"""
  # Clear singleton instances
  Aws._instances = {}
  
  with patch("services.aws.config", mock_config), \
       patch("builtins.open", mock_open(read_data=valid_csv_data)):
    
    aws1 = Aws(aws_secret_loc="/test/path")
    aws2 = Aws(aws_secret_loc="/test/path")
    
    assert aws1 is aws2
