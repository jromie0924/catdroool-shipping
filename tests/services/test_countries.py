import json
import os
import sys
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.countries import Countries


class MockConfig:
  APP_NAME = "test_app"
  AWS_DB_SECRET_NAME = "db_secret"


@pytest.fixture
def mock_aws():
  mock = MagicMock()
  db_secrets = {
    "dbname": "test_db",
    "username": "test_user",
    "password": "test_pass",
    "host": "localhost",
    "port": "5432"
  }
  mock.get_secret.return_value = json.dumps(db_secrets)
  return mock


@pytest.fixture
def mock_psycopg2_conn():
  mock_conn = MagicMock()
  mock_cursor = MagicMock()
  mock_conn.cursor.return_value = mock_cursor
  return mock_conn, mock_cursor


def test_countries_init(mock_aws, mock_psycopg2_conn):
  """Test Countries initialization"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn):
    
    countries = Countries()
    
    assert countries._conn == mock_conn
    assert countries._sql_path == 'sql'


def test_countries_singleton_behavior(mock_aws, mock_psycopg2_conn):
  """Test that Countries follows singleton pattern"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn):
    
    countries1 = Countries()
    countries2 = Countries()
    
    assert countries1 is countries2


def test_get_country_name_from_id_success(mock_aws, mock_psycopg2_conn):
  """Test successfully getting country name from code"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.fetchone.return_value = ("United States",)
  
  sql_content = "SELECT name FROM countries WHERE code = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    result = countries.get_country_name_from_id("US")
    
    assert result == "United States"
    mock_cursor.execute.assert_called_once_with(sql_content, ("US",))
    mock_cursor.close.assert_called_once()


def test_get_country_name_from_id_not_found(mock_aws, mock_psycopg2_conn):
  """Test getting country name when not found"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.fetchone.return_value = None
  
  sql_content = "SELECT name FROM countries WHERE code = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    result = countries.get_country_name_from_id("XX")
    
    assert result is None


def test_get_country_name_from_id_file_not_found(mock_aws, mock_psycopg2_conn):
  """Test getting country name when SQL file not found"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("os.path.isfile", return_value=False):
    
    countries = Countries()
    
    with pytest.raises(FileNotFoundError):
      countries.get_country_name_from_id("US")


def test_get_country_name_from_id_exception(mock_aws, mock_psycopg2_conn):
  """Test exception handling when getting country name"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.execute.side_effect = Exception("Database error")
  
  sql_content = "SELECT name FROM countries WHERE code = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    result = countries.get_country_name_from_id("US")
    
    # Should return None on exception
    assert result is None


def test_get_state_code_by_country_code_state_code_success(mock_aws, mock_psycopg2_conn):
  """Test successfully getting state code"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.fetchone.return_value = ("IL",)
  
  sql_content = "SELECT state_code FROM states WHERE country_code = %s AND state_code = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    result = countries.get_state_code_by_country_code_state_code("US", "IL")
    
    assert result == "IL"


def test_get_state_code_by_country_code_state_code_long_name(mock_aws, mock_psycopg2_conn):
  """Test getting state code when state name is provided instead of code"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.fetchone.return_value = ("IL",)
  
  sql_content = "SELECT state_code FROM states WHERE country_code = %s AND state_code = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    # Should call get_state_code_by_country_code_state_name for long names
    result = countries.get_state_code_by_country_code_state_code("US", "Illinois")
    
    assert result == "IL"


def test_get_state_code_by_country_code_state_code_empty(mock_aws, mock_psycopg2_conn):
  """Test that ValueError is raised when state code is empty"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn):
    
    countries = Countries()
    
    with pytest.raises(ValueError, match="State code cannot be None or empty"):
      countries.get_state_code_by_country_code_state_code("US", "")


def test_get_state_code_by_country_code_state_name_success(mock_aws, mock_psycopg2_conn):
  """Test successfully getting state code by name"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  mock_cursor.fetchone.return_value = ("IL",)
  
  sql_content = "SELECT state_code FROM states WHERE country_code = %s AND state_name = %s"
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn), \
       patch("builtins.open", mock_open(read_data=sql_content)), \
       patch("os.path.isfile", return_value=True):
    
    countries = Countries()
    result = countries.get_state_code_by_country_code_state_name("US", "Illinois")
    
    assert result == "IL"


def test_get_state_code_by_country_code_state_name_empty(mock_aws, mock_psycopg2_conn):
  """Test that ValueError is raised when state name is empty"""
  # Clear singleton instances
  Countries._instances = {}
  
  mock_conn, mock_cursor = mock_psycopg2_conn
  
  with patch("services.countries.Aws", return_value=mock_aws), \
       patch("services.countries.config", MockConfig), \
       patch("services.countries.psycopg2.connect", return_value=mock_conn):
    
    countries = Countries()
    
    with pytest.raises(ValueError, match="State code cannot be None or empty"):
      countries.get_state_code_by_country_code_state_name("US", "")
