import os
import sys
from datetime import datetime as dt
from unittest.mock import MagicMock, patch, call
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.trending import Trending, CUSTOMER_COUNT_DOMESTIC_KEY, CUSTOMER_COUNT_INTL_KEY, CUSTOMER_COUNT_TOTAL_KEY


class MockConfig:
  APP_NAME = "test_app"
  CATDROOOL_TRENDING_DYNAMODB_TABLE = "test_trending_table"


@pytest.fixture
def mock_dynamodb():
  mock = MagicMock()
  mock.put_item.return_value = None
  mock.get_latest_customer_metrics.return_value = {
    CUSTOMER_COUNT_DOMESTIC_KEY: 100,
    CUSTOMER_COUNT_INTL_KEY: 50,
    CUSTOMER_COUNT_TOTAL_KEY: 150
  }
  return mock


def test_trending_init(mock_dynamodb):
  """Test Trending initialization"""
  # Clear singleton instances
  Trending._instances = {}
  
  with patch("services.trending.DynamoDB", return_value=mock_dynamodb), \
       patch("services.trending.config", MockConfig):
    
    trending = Trending()
    assert trending._dynamodb == mock_dynamodb


def test_trending_singleton_behavior(mock_dynamodb):
  """Test that Trending follows singleton pattern"""
  # Clear singleton instances
  Trending._instances = {}
  
  with patch("services.trending.DynamoDB", return_value=mock_dynamodb), \
       patch("services.trending.config", MockConfig):
    
    trending1 = Trending()
    trending2 = Trending()
    
    assert trending1 is trending2


def test_build_trending_item():
  """Test building a trending item with current timestamp"""
  # Clear singleton instances
  Trending._instances = {}
  
  mock_dynamodb = MagicMock()
  
  with patch("services.trending.DynamoDB", return_value=mock_dynamodb), \
       patch("services.trending.config", MockConfig):
    
    trending = Trending()
    
    # Mock datetime
    mock_dt = dt(2024, 3, 15, 12, 30, 45)
    with patch("services.trending.dt") as mock_datetime:
      mock_datetime.now.return_value = mock_dt
      
      result = trending.build_trending_item(cust_dom=100, cust_intl=50)
      
      assert result["year"] == 2024
      assert result["month"] == 3
      assert result["day"] == 15
      assert result[CUSTOMER_COUNT_DOMESTIC_KEY] == 100
      assert result[CUSTOMER_COUNT_INTL_KEY] == 50
      assert result[CUSTOMER_COUNT_TOTAL_KEY] == 150
      assert "timestamp" in result


def test_compare_items():
  """Test comparing two trending items"""
  this_item = {
    CUSTOMER_COUNT_DOMESTIC_KEY: 120,
    CUSTOMER_COUNT_INTL_KEY: 60,
    CUSTOMER_COUNT_TOTAL_KEY: 180
  }
  
  that_item = {
    CUSTOMER_COUNT_DOMESTIC_KEY: 100,
    CUSTOMER_COUNT_INTL_KEY: 50,
    CUSTOMER_COUNT_TOTAL_KEY: 150
  }
  
  result = Trending.compare_items(this_item, that_item)
  
  assert result["domestic"]["current_count"] == 120
  assert result["domestic"]["diff"] == "20"
  assert result["domestic"]["perc"] == "20.0%"
  
  assert result["intl"]["current_count"] == 60
  assert result["intl"]["diff"] == "10"
  assert result["intl"]["perc"] == "20.0%"
  
  assert result["total"]["current_count"] == 180
  assert result["total"]["diff"] == "30"
  assert result["total"]["perc"] == "20.0%"


def test_compare_items_negative_change():
  """Test comparing items with negative change"""
  this_item = {
    CUSTOMER_COUNT_DOMESTIC_KEY: 80,
    CUSTOMER_COUNT_INTL_KEY: 40,
    CUSTOMER_COUNT_TOTAL_KEY: 120
  }
  
  that_item = {
    CUSTOMER_COUNT_DOMESTIC_KEY: 100,
    CUSTOMER_COUNT_INTL_KEY: 50,
    CUSTOMER_COUNT_TOTAL_KEY: 150
  }
  
  result = Trending.compare_items(this_item, that_item)
  
  assert result["domestic"]["diff"] == "-20"
  assert result["domestic"]["perc"] == "-20.0%"


def test_analyze_customer_counts(mock_dynamodb):
  """Test analyzing customer counts"""
  # Clear singleton instances
  Trending._instances = {}
  
  with patch("services.trending.DynamoDB", return_value=mock_dynamodb), \
       patch("services.trending.config", MockConfig):
    
    trending = Trending()
    customers_domestic = [{"id": i} for i in range(120)]
    customers_intl = [{"id": i} for i in range(60)]
    
    with patch.object(trending, 'build_trending_item') as mock_build:
      mock_build.return_value = {
        CUSTOMER_COUNT_DOMESTIC_KEY: 120,
        CUSTOMER_COUNT_INTL_KEY: 60,
        CUSTOMER_COUNT_TOTAL_KEY: 180
      }
      
      result = trending.analyze_customer_counts(customers_domestic, customers_intl)
      
      mock_build.assert_called_once_with(cust_dom=120, cust_intl=60)
      mock_dynamodb.put_item.assert_called_once()
      
      assert "domestic" in result
      assert "intl" in result
      assert "total" in result


def test_analyze_customer_counts_no_previous_data(mock_dynamodb):
  """Test analyzing customer counts when no previous data exists"""
  # Clear singleton instances
  Trending._instances = {}
  
  mock_dynamodb.get_latest_customer_metrics.return_value = None
  
  with patch("services.trending.DynamoDB", return_value=mock_dynamodb), \
       patch("services.trending.config", MockConfig):
    
    trending = Trending()
    customers_domestic = [{"id": i} for i in range(100)]
    customers_intl = [{"id": i} for i in range(50)]
    
    result = trending.analyze_customer_counts(customers_domestic, customers_intl)
    
    # When no previous data, should compare with itself (0% change)
    assert result["domestic"]["perc"] == "0.0%"
    assert result["intl"]["perc"] == "0.0%"


def test_build_metrics_comparison_report():
  """Test building metrics comparison Excel report"""
  comparison_obj = {
    "domestic": {
      "current_count": 120,
      "diff": "20",
      "perc": "20.0%"
    },
    "intl": {
      "current_count": 60,
      "diff": "10",
      "perc": "20.0%"
    },
    "total": {
      "current_count": 180,
      "diff": "30",
      "perc": "20.0%"
    }
  }
  
  with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
    filename = tmp.name
  
  try:
    # This should create a valid Excel file without errors
    Trending.build_metrics_comparison_report(filename, comparison_obj)
    
    # Verify file was created
    assert os.path.exists(filename)
    assert os.path.getsize(filename) > 0
  finally:
    # Cleanup
    if os.path.exists(filename):
      os.remove(filename)
