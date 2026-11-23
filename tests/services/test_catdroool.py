import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import stripe
from stripe._stripe_object import StripeObject

from config import config
from services.catdroool import NO_BDAY, UNPARSEABLE, Catdroool, sort_by_field_alphabetically

CUSTOMER = StripeObject.construct_from({'id': 'cus_1'}, key='sk_test')


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


class TestGetBirthdayMonth:
  """get_birthday_month reads a free-text checkout custom field, so the input is whatever the
  customer typed. Stripe is mocked at Session.list; dateparser and SpellChecker run for real,
  because their behavior on messy input is the thing under test.
  """

  @pytest.fixture
  def catdroool(self):
    # Bypass __init__: it pulls secrets from AWS and sends a startup email.
    instance = Catdroool.__new__(Catdroool)
    instance._stripe_api_key = 'sk_test'
    return instance

  @staticmethod
  def _field(key: str, value):
    return {'key': key, 'type': 'text', 'text': {'value': value}}

  @classmethod
  def _sessions(cls, *custom_field_lists) -> StripeObject:
    """Build a Session.list response; one session per argument, newest first (Stripe's order)."""
    return StripeObject.construct_from({
      'object': 'list',
      'data': [{'id': f'cs_{i}', 'custom_fields': fields} for i, fields in enumerate(custom_field_lists)],
    }, key='sk_test')

  @classmethod
  def _birthday_sessions(cls, text):
    return cls._sessions([cls._field(config.BIRTHDAY_FIELD_KEY, text)])

  def _month_for(self, catdroool, text) -> int:
    with patch.object(stripe.checkout.Session, 'list', return_value=self._birthday_sessions(text)):
      return catdroool.get_birthday_month(customer=CUSTOMER)

  # --- Stripe plumbing ---------------------------------------------------------------------

  def test_queries_completed_sessions_for_the_given_customer(self, catdroool):
    # status='complete' is what keeps an abandoned (expired) checkout -- newer, but with no
    # answer -- from shadowing the real one. Stripe does the filtering, so the mock can't
    # exercise it; this pins that the filter is actually sent.
    with patch.object(stripe.checkout.Session, 'list', return_value=self._birthday_sessions('March')) as mock_list:
      catdroool.get_birthday_month(customer=CUSTOMER)

    mock_list.assert_called_once_with(api_key='sk_test', customer='cus_1', status='complete')

  def test_no_checkout_sessions_returns_sentinel(self, catdroool):
    with patch.object(stripe.checkout.Session, 'list', return_value=self._sessions()):
      assert catdroool.get_birthday_month(customer=CUSTOMER) == NO_BDAY

  def test_session_without_custom_fields_returns_sentinel(self, catdroool):
    with patch.object(stripe.checkout.Session, 'list', return_value=self._sessions([])):
      assert catdroool.get_birthday_month(customer=CUSTOMER) == NO_BDAY

  def test_session_with_only_other_custom_fields_returns_sentinel(self, catdroool):
    with patch.object(stripe.checkout.Session, 'list', return_value=self._sessions([self._field('catsname', 'Biscuit')])):
      assert catdroool.get_birthday_month(customer=CUSTOMER) == NO_BDAY

  def test_finds_birthday_among_other_custom_fields(self, catdroool):
    # A non-text field (dropdown) has no text payload; it must be filtered out before .text is
    # touched, or it would raise.
    dropdown = {'key': 'favoriteflavor', 'type': 'dropdown', 'dropdown': {'value': 'tuna'}, 'text': None}
    fields = [dropdown, self._field('catsname', 'Biscuit'), self._field(config.BIRTHDAY_FIELD_KEY, 'October')]
    with patch.object(stripe.checkout.Session, 'list', return_value=self._sessions(fields)):
      assert catdroool.get_birthday_month(customer=CUSTOMER) == 10

  def test_uses_most_recent_session_when_it_has_a_birthday(self, catdroool):
    sessions = self._sessions(
      [self._field(config.BIRTHDAY_FIELD_KEY, 'April')],
      [self._field(config.BIRTHDAY_FIELD_KEY, 'August')],
    )
    with patch.object(stripe.checkout.Session, 'list', return_value=sessions):
      assert catdroool.get_birthday_month(customer=CUSTOMER) == 4

  # --- Parsing: well-formed input ----------------------------------------------------------

  @pytest.mark.parametrize('text, expected', [
    ('January', 1), ('february', 2), ('MARCH', 3), ('April', 4), ('May', 5), ('June', 6),
    ('July', 7), ('August', 8), ('September', 9), ('October', 10), ('November', 11), ('December', 12),
  ])
  def test_full_month_names(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  @pytest.mark.parametrize('text, expected', [
    ('Jan', 1), ('feb', 2), ('Mar', 3), ('apr', 4), ('Jun', 6), ('Jul', 7),
    ('aug', 8), ('Sep', 9), ('Sept', 9), ('oct', 10), ('Nov', 11), ('dec.', 12),
  ])
  def test_abbreviations(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  @pytest.mark.parametrize('text, expected', [
    ('June 5th', 6),
    ('5 June', 6),
    ('june!', 6),
    ('1990-06-15', 6),
    ('06/15/1990', 6),
    ('6/15', 6),
    ('15/6', 6),   # unambiguous day-first still resolves
  ])
  def test_full_dates(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  def test_ambiguous_numeric_date_is_read_month_first(self, catdroool):
    # US customers; 01/02 is January 2nd, not 1 February.
    assert self._month_for(catdroool, '01/02') == 1

  @pytest.mark.parametrize('text, expected', [('1', 1), ('06', 6), ('12', 12)])
  def test_bare_month_number(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  # --- Parsing: misspellings and sentences (SpellChecker fallback) --------------------------

  @pytest.mark.parametrize('text, expected', [
    ('Febuary', 2), ('Feburary', 2), ('Septmber', 9), ('Octobr', 10),
  ])
  def test_misspelled_month(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  @pytest.mark.parametrize('text, expected', [
    ('my birthday is in june', 6),
    ('its in may', 5),
  ])
  def test_month_inside_a_sentence(self, catdroool, text, expected):
    assert self._month_for(catdroool, text) == expected

  # --- Parsing: no usable month ------------------------------------------------------------

  @pytest.mark.parametrize('text', [
    'none', 'idk', 'summer', 'Christmas', 'not sure', 'prefer not to say',
    # dateparser read each of these as a month when it was allowed to auto-detect a language.
    'no', 'now', 'ok', 'x',
  ])
  def test_unparseable_text_returns_unparseable(self, catdroool, text):
    assert self._month_for(catdroool, text) == UNPARSEABLE

  # None is what Stripe sends when an optional text field is left blank. Blank is "no answer",
  # not "unparseable" -- it must not land in the error file.
  @pytest.mark.parametrize('text', [None, '', '   '])
  def test_blank_field_returns_no_bday(self, catdroool, text):
    assert self._month_for(catdroool, text) == NO_BDAY

  # Regression: dateparser's defaults filled a missing month from today, and generate_report
  # matches on today's month -- so every one of these would have been flagged every run.
  # Asserting -1 (never a real month) keeps this independent of when the suite runs.
  @pytest.mark.parametrize('text', [
    'N/A', 'n/a', 'na', 'NA',                            # no month at all
    '13', '25',                                          # a day with no month
    'today', 'yesterday', 'next month', 'in 2 weeks',    # relative to today
  ])
  def test_input_without_a_month_does_not_resolve_to_current_month(self, catdroool, text):
    assert self._month_for(catdroool, text) == UNPARSEABLE

  def test_relative_phrase_still_yields_a_named_month(self, catdroool):
    # Relative parsing is off, but the spellchecker fallback still finds the month word.
    assert self._month_for(catdroool, 'last june') == 6
