

import csv
import json
import logging
import os
import time
import stripe

from config import config
from datetime import datetime as dt
from exceptions.addressNotFoundException import AddressNotFoundException
from common import utils
from models.error import ErrorCollection
from services.aws import Aws
from services.countries import Countries
from services.domestics import Domestics
from services.emailer import Emailer


logger = logging.getLogger(config.APP_NAME)

class Catdroool:
  def __init__(self):
    self._aws = Aws()
    key_dict = json.loads(self._aws.get_secret(key=config.STRIPE_SECRET_KEY, type=str))
    self._stripe_api_key = key_dict.get(config.STRIPE_SECRET_KEY)
    self._date_str = dt.now().strftime(config.DATE_FORMAT_STRING)
    self._countries = Countries()
    self._error_collection = ErrorCollection()
    self._domestics = Domestics()
    self._emailer = Emailer()
    
  def generate_report(self):
    products = stripe.Product.search(api_key=self._stripe_api_key, query=f"name~'{config.PRODUCT_FILTER}'")
    catdrool_product_codes_domestic = [p.get('id') for p in products if config.INTERNATIONAL_FILTER.lower() not in p.get('name').lower()]
    catdrool_product_codes_intl = [p.get('id') for p in products if config.INTERNATIONAL_FILTER.lower() in p.get('name').lower()]

    subscriptions = []
    subs = stripe.Subscription.list(api_key=self._stripe_api_key, status='active')
    subscriptions.extend(subs['data'])
    while subs.has_more:
      time.sleep(0.05) # rate limit
      starts_after = subs['data'][-1]['id']
      subs = stripe.Subscription.list(api_key=self._stripe_api_key, status='active', starting_after=starts_after)
      subscriptions.extend(subs['data'])
      

    customers_domestic: list[dict] = []
    customers_intl: list[dict] = []

    for sub in subscriptions:
      product_codes_domestic = [i['plan']['product'] for i in sub['items']['data'] if i['plan']['product'] in catdrool_product_codes_domestic]
      product_codes_intl = [i['plan']['product'] for i in sub['items']['data'] if i['plan']['product'] in catdrool_product_codes_intl]
      if len(product_codes_domestic):
        cust_id = sub['customer']
        customer = stripe.Customer.retrieve(api_key=self._stripe_api_key, id=cust_id)
        customers_domestic.append(customer)
        time.sleep(0.05) # rate limit
      if len(product_codes_intl):
        cust_id = sub.get('customer')
        customer = stripe.Customer.retrieve(api_key=self._stripe_api_key, id=cust_id)
        customers_intl.append(customer)
    
    # with open('customers_domestic.json', 'r') as file:
    #   customers_domestic = json.load(file)
      
    # with open("customers_intl.json", "r") as file:
    #   customers_intl = json.load(file)


    shipping_records_domestic: list[dict] = []
    shipping_records_intl: list[dict] = []
    directory = f'output/{self._date_str}/'
    filename_domestic = f'{directory}Catdrool-shipping-record_domestic_{self._date_str}.csv'
    filename_intl = f'{directory}Catdrool-shipping-record_international_{self._date_str}.csv'
    filename_error = f'{directory}Catdrool-shipping-errors_{self._date_str}.csv'
    keys_domestic: list[str] = []
    keys_intl: list[str] = []
    
    os.makedirs(os.path.dirname(directory), exist_ok=True)
    
    for customer in customers_domestic:
      try:
        
        shipping_info = customer['shipping']['address'] if customer['shipping'] and customer['shipping']['address'] else {}
        usps_verified_address = self._domestics.validate_address(address_1=shipping_info.get("line1"),
                                                                 address_2=shipping_info.get("line2"),
                                                                 city=shipping_info.get("city"),
                                                                 zip=shipping_info.get("postal_code"),
                                                                 state=shipping_info.get("state"))

        record = utils.populate_shipment_record(customer=customer, usps_verified_address=usps_verified_address)
        
        if not keys_domestic:
          keys_domestic = record.keys()
        shipping_records_domestic.append(record)
        
        if not shipping_info:
          self._error_collection.add_new(customer_id=customer['id'],
                               issue="Customer shipping information missing.",
                               nationality="DOMESTIC")
      except AddressNotFoundException as e:
        logger.error(f"Address information for customer {customer['id']} was not recognized by USPS.")
        self._error_collection.add_new(customer_id=customer['id'], issue="Address information not identified by USPS.", nationality="DOMESTIC")
      except Exception as e:
        logger.error(f"failed on customer: {customer['id']}")
        self._error_collection.add_new(customer_id=customer['id'], issue="An error occured when processing this customer.", nationality="DOMESTIC")
    with open(filename_domestic, 'w') as f:
      writer = csv.DictWriter(f, fieldnames=keys_domestic)
      writer.writeheader()
      writer.writerows(shipping_records_domestic)

    logger.info(f"Records written to {filename_domestic}")


    for customer in customers_intl:
      try:
        shipping_info = customer['shipping']['address'] if customer['shipping'] and customer['shipping']['address'] else {}
        country = self._countries.get_country_name_from_id(country_code = shipping_info.get('country'))
        state = ""
        if shipping_info["state"]:
          if self._countries.get_state_code_by_country_code_state_code(country_code=shipping_info.get("country"), state_code=shipping_info["state"]):
            state = shipping_info["state"]
          else:
            self._error_collection.add_new(customer_id=customer['id'],
                                 issue=f"Shipping state code {shipping_info["state"]} is not registered in world database for the country of {country}.",
                                 nationality="INTERNATIONAL")

        record = {
          "CardName": customer.get('name'),
          "ShippingName": customer.get('shipping').get('name'),
          "ShippingAddressLine1": shipping_info.get('line1'),
          "ShippingAddressLine2": shipping_info.get('line2') or "",
          "IntlShippingAddressLine1": f"{shipping_info.get('line1')}, {shipping_info.get('line2') or ''}",
          "ShippingAddressCity": shipping_info.get('city'),
          "shippingAddressState": state,
          "ShippingAddressPostalCode": shipping_info.get('postal_code') or "",
          "IntlShippingAddressLine2": f"{shipping_info.get('city')} {state or ''} {shipping_info.get('postal_code')}",
          "ShippingCountry": country
        }
        if not keys_intl:
          keys_intl = record.keys()
        shipping_records_intl.append(record)
        
        if not shipping_info:
          self._error_collection.add_new(customer_id=customer['id'], issue="Customer shipping information missing.", nationality='INTERNATIONAL')
        
      except Exception as e:
        logger.error(f"failed on customer: {customer['id']}")
        self._error_collection.add_new(customer_id=customer['id'], issue="An error occured when processing this customer.", nationality="INTERNATIONAL")
    with open(filename_intl, 'w') as f:
      writer = csv.DictWriter(f, fieldnames=keys_intl)
      writer.writeheader()
      writer.writerows(shipping_records_intl)
      
    with open(filename_error, 'w') as file:
      writer = csv.DictWriter(file, fieldnames=ErrorCollection.FIELD_NAMES)
      writer.writeheader()
      writer.writerows(self._error_collection.errors)

    logger.info(f"Records written to {filename_intl}")
    
    # TODO: Distribute the three files via the Emailer class.