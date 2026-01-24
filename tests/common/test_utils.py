import os
import sys
from datetime import datetime as dt

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from common import utils


class TestUtils:
  def test_get_time_difference_hours(self):
    """Test time difference calculation in hours"""
    start = 1000000000000  # milliseconds
    end = 1000003600000    # 1 hour later
    
    result = utils.get_time_difference_hours(start, end)
    assert result == 1.0
  
  def test_get_time_difference_hours_zero(self):
    """Test time difference when start equals end"""
    timestamp = 1000000000000
    result = utils.get_time_difference_hours(timestamp, timestamp)
    assert result == 0.0
  
  def test_get_previous_month_january(self):
    """Test previous month calculation for January"""
    result = utils.get_previous_month(1)
    assert result == 12
  
  def test_get_previous_month_february(self):
    """Test previous month calculation for February"""
    result = utils.get_previous_month(2)
    assert result == 1
  
  def test_get_previous_month_december(self):
    """Test previous month calculation for December"""
    result = utils.get_previous_month(12)
    assert result == 11
  
  def test_get_previous_month_no_param(self):
    """Test previous month calculation without parameter uses current month"""
    result = utils.get_previous_month()
    current_month = dt.now().month
    expected = (current_month - 2) % 12 + 1
    assert result == expected
  
  def test_populate_shipment_record_with_usps_address(self):
    """Test shipment record population with USPS verified address"""
    customer = {
      'name': 'John Doe',
      'shipping': {
        'name': 'John Doe',
        'address': {
          'line1': '123 Main St',
          'line2': 'Apt 4',
          'city': 'Springfield',
          'state': 'IL',
          'postal_code': '62701'
        }
      }
    }
    
    usps_verified_address = {
      'streetAddress': '123 Main Street',
      'secondaryAddress': 'Apt 4',
      'city': 'Springfield',
      'state': 'IL',
      'ZIPCode': '62701',
      'ZIPPlus4': '1234'
    }
    
    result = utils.populate_shipment_record(customer, usps_verified_address)
    
    assert result['CardName'] == 'John Doe'
    assert result['ShippingName'] == 'John Doe'
    assert result['ShippingAddressLine1'] == '123 Main Street'
    assert result['ShippingAddressLine2'] == 'Apt 4'
    assert result['ShippingAddressCity'] == 'Springfield'
    assert result['ShippingAddressState'] == 'IL'
    assert result['ShippingAddressPostalCode'] == '62701-1234'
    assert result['#Line2Visibility'] == 'True'
  
  def test_populate_shipment_record_without_usps_address(self):
    """Test shipment record population without USPS verified address"""
    customer = {
      'name': 'Jane Smith',
      'shipping': {
        'name': 'Jane Smith',
        'address': {
          'line1': '456 Oak Ave',
          'line2': '',
          'city': 'Chicago',
          'state': 'IL',
          'postal_code': '60601'
        }
      }
    }
    
    usps_verified_address = {}
    
    result = utils.populate_shipment_record(customer, usps_verified_address)
    
    assert result['CardName'] == 'Jane Smith'
    assert result['ShippingName'] == 'Jane Smith'
    assert result['ShippingAddressLine1'] == '456 Oak Ave'
    assert result['ShippingAddressLine2'] == ''
    assert result['ShippingAddressCity'] == 'Chicago'
    assert result['ShippingAddressState'] == 'IL'
    assert result['ShippingAddressPostalCode'] == '60601'
    assert result['#Line2Visibility'] == 'False'
  
  def test_populate_shipment_record_missing_shipping_info(self):
    """Test that exception is raised when shipping info is missing"""
    customer = {
      'name': 'Test User',
      'shipping': None
    }
    
    with pytest.raises(Exception, match="Shipping information missing"):
      utils.populate_shipment_record(customer, {})
  
  def test_populate_shipment_record_invalid_zip(self):
    """Test handling of invalid ZIP code from USPS"""
    customer = {
      'name': 'John Doe',
      'shipping': {
        'name': 'John Doe',
        'address': {
          'line1': '123 Main St',
          'line2': '',
          'city': 'Springfield',
          'state': 'IL',
          'postal_code': '62701'
        }
      }
    }
    
    usps_verified_address = {
      'streetAddress': '123 Main Street',
      'city': 'Springfield',
      'state': 'IL',
      'ZIPCode': '62701',
      'ZIPPlus4': ''  # Invalid - will create "62701-"
    }
    
    result = utils.populate_shipment_record(customer, usps_verified_address)
    
    # Should fall back to Stripe postal code when USPS zip is invalid
    assert result['ShippingAddressPostalCode'] == '62701'
