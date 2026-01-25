import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.catdroool import sort_by_field_alphabetically


class TestCatdrooolUtilities:
  def test_sort_by_field_alphabetically_basic(self):
    """Test sorting a mailing list by city"""
    mailing_list = [
      {"ShippingAddressCity": "Chicago", "name": "John"},
      {"ShippingAddressCity": "Austin", "name": "Jane"},
      {"ShippingAddressCity": "Boston", "name": "Bob"}
    ]
    
    result = sort_by_field_alphabetically(mailing_list)
    
    assert result[0]["ShippingAddressCity"] == "Austin"
    assert result[1]["ShippingAddressCity"] == "Boston"
    assert result[2]["ShippingAddressCity"] == "Chicago"
  
  def test_sort_by_field_alphabetically_case_insensitive(self):
    """Test that sorting is case-insensitive"""
    mailing_list = [
      {"ShippingAddressCity": "chicago", "name": "John"},
      {"ShippingAddressCity": "AUSTIN", "name": "Jane"},
      {"ShippingAddressCity": "Boston", "name": "Bob"}
    ]
    
    result = sort_by_field_alphabetically(mailing_list)
    
    # Should sort: AUSTIN, Boston, chicago
    assert result[0]["ShippingAddressCity"] == "AUSTIN"
    assert result[1]["ShippingAddressCity"] == "Boston"
    assert result[2]["ShippingAddressCity"] == "chicago"
  
  def test_sort_by_field_alphabetically_empty_list(self):
    """Test sorting an empty list"""
    result = sort_by_field_alphabetically([])
    assert result == []
  
  def test_sort_by_field_alphabetically_single_item(self):
    """Test sorting a list with one item"""
    mailing_list = [{"ShippingAddressCity": "Chicago", "name": "John"}]
    result = sort_by_field_alphabetically(mailing_list)
    assert len(result) == 1
    assert result[0]["ShippingAddressCity"] == "Chicago"
  
  def test_sort_by_field_alphabetically_duplicate_values(self):
    """Test sorting with duplicate city names"""
    mailing_list = [
      {"ShippingAddressCity": "Chicago", "name": "John"},
      {"ShippingAddressCity": "Austin", "name": "Jane"},
      {"ShippingAddressCity": "Chicago", "name": "Bob"}
    ]
    
    result = sort_by_field_alphabetically(mailing_list)
    
    assert result[0]["ShippingAddressCity"] == "Austin"
    assert result[1]["ShippingAddressCity"] == "Chicago"
    assert result[2]["ShippingAddressCity"] == "Chicago"
    assert len(result) == 3
