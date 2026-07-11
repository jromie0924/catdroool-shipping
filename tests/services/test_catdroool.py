import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from stripe._stripe_object import StripeObject

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


class TestStripeObjectBoundary:
  """The SDK returns StripeObject, not dict. generate_report and populate_shipment_record both
  lean on .get() for optional fields, so every Stripe object is converted at the boundary.
  These pin that contract: an unpinned SDK bump once removed .get() and took a prod run down
  with AttributeError, and nothing caught it because the other tests mock Stripe as plain dicts.
  """

  @staticmethod
  def _customer() -> StripeObject:
    return StripeObject.construct_from({
      'id': 'cus_1',
      'name': 'Jackson Romie',
      'shipping': {
        'name': 'Jackson Romie',
        'address': {'line1': '809 S Lamar Blvd', 'city': 'Austin',
                    'state': 'TX', 'postal_code': '78704'},
      },
    }, key='sk_test')

  def test_raw_stripe_object_has_no_get(self):
    # The bug itself: .get() is not a method on StripeObject, it falls through to __getattr__.
    with pytest.raises(AttributeError):
      self._customer().get('id')

  def test_to_dict_is_recursive(self):
    # The fix depends on to_dict() converting nested objects too -- shipping.address is where
    # the .get() calls actually land.
    customer = self._customer().to_dict()

    assert isinstance(customer, dict)
    assert isinstance(customer['shipping'], dict)
    assert isinstance(customer['shipping']['address'], dict)

  def test_converted_customer_supports_the_access_the_report_relies_on(self):
    customer = self._customer().to_dict()
    shipping_info = customer['shipping']['address']

    assert customer.get('name') == 'Jackson Romie'
    assert customer.get('shipping').get('name') == 'Jackson Romie'
    assert shipping_info.get('line1') == '809 S Lamar Blvd'
    # Absent optional field must return None rather than raise -- this is why the code cannot
    # simply be rewritten to use [] subscripting instead of .get().
    assert shipping_info.get('line2') is None
