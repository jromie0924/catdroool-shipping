import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.dynamodb import DynamoDB


class MockConfig:
  APP_NAME = "test_app"
  CATDROOOL_TRENDING_DYNAMO_PARTITION_KEY = "month"


@pytest.fixture
def mock_aws():
  mock = MagicMock()
  mock.dynamodb_resource = MagicMock()
  return mock


@pytest.fixture
def mock_table():
  mock = MagicMock()
  mock.put_item.return_value = None
  mock.query.return_value = {
    "Items": [
      {
        "month": "2024-01",
        "domestic_customer_count": 100,
        "international_customer_count": 50,
        "total_customer_count": 150
      }
    ]
  }
  return mock


def test_dynamodb_init(mock_aws):
  """Test DynamoDB initialization"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig):
    
    db = DynamoDB()
    assert db.dynamodb_resource == mock_aws.dynamodb_resource


def test_dynamodb_singleton_behavior(mock_aws):
  """Test that DynamoDB follows singleton pattern"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig):
    
    db1 = DynamoDB()
    db2 = DynamoDB()
    
    assert db1 is db2


def test_put_item_success(mock_aws, mock_table):
  """Test successfully putting an item into DynamoDB"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  mock_aws.dynamodb_resource.Table.return_value = mock_table
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig):
    
    db = DynamoDB()
    item = {"id": "test", "value": 123}
    db.put_item(item=item, table_name="test_table")
    
    mock_table.put_item.assert_called_once_with(Item=item)


def test_put_item_exception(mock_aws):
  """Test put_item handles exceptions gracefully"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  mock_table = MagicMock()
  mock_table.put_item.side_effect = Exception("DynamoDB Error")
  mock_aws.dynamodb_resource.Table.return_value = mock_table
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig):
    
    db = DynamoDB()
    # Should not raise exception
    db.put_item(item={"id": "test"}, table_name="test_table")


def test_get_latest_customer_metrics_success(mock_aws, mock_table):
  """Test successfully retrieving latest customer metrics"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  mock_aws.dynamodb_resource.Table.return_value = mock_table
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig), \
       patch("services.dynamodb.utils.get_previous_month", return_value=1):
    
    db = DynamoDB()
    result = db.get_latest_customer_metrics("test_table")
    
    assert result is not None
    assert result["month"] == "2024-01"
    assert result["domestic_customer_count"] == 100


def test_get_latest_customer_metrics_no_items(mock_aws):
  """Test get_latest_customer_metrics when no items are returned"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  mock_table = MagicMock()
  mock_table.query.return_value = {"Items": []}
  mock_aws.dynamodb_resource.Table.return_value = mock_table
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig), \
       patch("services.dynamodb.utils.get_previous_month", return_value=1):
    
    db = DynamoDB()
    result = db.get_latest_customer_metrics("test_table")
    
    assert result is None


def test_get_latest_customer_metrics_exception(mock_aws):
  """Test get_latest_customer_metrics handles exceptions gracefully"""
  # Clear singleton instances
  DynamoDB._instances = {}
  
  mock_table = MagicMock()
  mock_table.query.side_effect = Exception("DynamoDB Error")
  mock_aws.dynamodb_resource.Table.return_value = mock_table
  
  with patch("services.dynamodb.Aws", return_value=mock_aws), \
       patch("services.dynamodb.config", MockConfig), \
       patch("services.dynamodb.utils.get_previous_month", return_value=1):
    
    db = DynamoDB()
    result = db.get_latest_customer_metrics("test_table")
    
    assert result is None
