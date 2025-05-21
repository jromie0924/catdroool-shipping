import stripe
import time
from datetime import datetime as dt
import csv
from countries import Countries
from services.stripeService import StripeService
from config import constants


date_str = dt.now().strftime(constants.FORMAT_STRING)

countries = Countries()

stripe_api_key = ''
country_api_key = ''

products = stripe.Product.search(api_key=stripe_api_key, query=f"name~'{constants.PRODUCT_FILTER}'")
catdrool_product_codes_domestic = [p.get('id') for p in products if constants.INTERNATIONAL_FILTER.lower() not in p.get('name').lower()]
catdrool_product_codes_intl = [p.get('id') for p in products if constants.INTERNATIONAL_FILTER.lower() in p.get('name').lower()]

subscriptions = []
subs = stripe.Subscription.list(api_key=stripe_api_key, status='active')
subscriptions.extend(subs['data'])
while subs.has_more:
  time.sleep(0.05) # rate limit
  starts_after = subs['data'][-1]['id']
  subs = stripe.Subscription.list(api_key=stripe_api_key, status='active', starting_after=starts_after)
  subscriptions.extend(subs['data'])
  

customers_domestic: list[dict] = []
customers_intl: list[dict] = []

for sub in subscriptions:
  product_codes_domestic = [i['plan']['product'] for i in sub['items']['data'] if i['plan']['product'] in catdrool_product_codes_domestic]
  product_codes_intl = [i['plan']['product'] for i in sub['items']['data'] if i['plan']['product'] in catdrool_product_codes_intl]
  if len(product_codes_domestic):
    cust_id = sub['customer']
    customer = stripe.Customer.retrieve(api_key=stripe_api_key, id=cust_id)
    customers_domestic.append(customer)
    time.sleep(0.05) # rate limit
  if len(product_codes_intl):
    cust_id = sub.get('customer')
    customer = stripe.Customer.retrieve(api_key=stripe_api_key, id=cust_id)
    customers_intl.append(customer)


    

shipping_records_domestic: list[dict] = []
shipping_records_intl: list[dict] = []
filename_domestic = f'Catdrool-shipping-record_domestic_{date_str}.csv'
filename_intl = f'Catdrool-shipping-record_international_{date_str}.csv'
keys_domestic: list[str] = []
keys_intl: list[str] = []
for customer in customers_domestic:
  try:
    shipping_info = customer['shipping']['address']
    line_2_visibility: bool = bool(shipping_info.get('line2'))
    record = {
      "CardName": customer.get('name'),
      "ShippingName": customer.get('shipping').get('name'),
      "ShippingAddressLine1": shipping_info.get('line1'),
      "ShippingAddressLine2": shipping_info.get('line2'),
      "#Line2Visibility": f"{line_2_visibility}",
      "ShippingAddressCity": shipping_info.get('city'),
      "ShippingAddressState": shipping_info.get('state'),
      "ShippingAddressPostalCode": shipping_info.get('postal_code'),
      "ShippingAddressLine3": f"{shipping_info.get('city')} {shipping_info.get('state')} {shipping_info.get('postal_code')}"
    }
    if not keys_domestic:
      keys_domestic = record.keys()
    shipping_records_domestic.append(record)
  except Exception as e:
    print(f"failed on customer: {customer['id']}")
with open(filename_domestic, 'w') as f:
  writer = csv.DictWriter(f, fieldnames=keys_domestic)
  writer.writeheader()
  writer.writerows(shipping_records_domestic)

print(f"Records written to {filename_domestic}")


for customer in customers_intl:
  try:
    shipping_info = customer['shipping']['address']
    # country = countries.getCountryName(country_code=shipping_info.get('country')) or shipping_info.get('country')
    country = countries.get_country_name(country_code = shipping_info.get('country'))
    state = shipping_info.get('state') if countries.validate_state_code(country_code=country, state_code=shipping_info.get('state')) else ""
    record = {
      "CardName": customer.get('name'),
      "ShippingName": customer.get('shipping').get('name'),
      "ShippingAddressLine1": shipping_info.get('line1'),
      "ShippingAddressLine2": shipping_info.get('line2'),
      "IntlShippingAddressLine1": f"{shipping_info.get('line1')}, {shipping_info.get('line2') or ''}",
      "ShippingAddressCity": shipping_info.get('city'),
      "shippingAddressState": state,
      "ShippingAddressPostalCode": shipping_info.get('postal_code'),
      "IntlShippingAddressLine2": f"{shipping_info.get('city')}\t{state or ''}\t{shipping_info.get('postal_code')}",
      "ShippingCountry": country
    }
    if not keys_intl:
      keys_intl = record.keys()
    shipping_records_intl.append(record)
  except Exception as e:
    print(f"failed on customer: {customer['id']}")
with open(filename_intl, 'w') as f:
  writer = csv.DictWriter(f, fieldnames=keys_intl)
  writer.writeheader()
  writer.writerows(shipping_records_intl)

print(f"Records written to {filename_intl}")
