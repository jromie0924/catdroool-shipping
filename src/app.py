import stripe
import time
from datetime import datetime as dt
import csv
from services.stripeService import StripeService


PRODUCT_FILTER = "Catdroool Club"
FORMAT_STRING = "%Y-%m-%d"

date_str = dt.now().strftime(FORMAT_STRING)

key = ''

products = stripe.Product.search(api_key=key, query=f"name~'{PRODUCT_FILTER}'")
catdrool_product_codes = [p['id'] for p in products]

subscriptions = []
subs = stripe.Subscription.list(api_key=key, status='active')
subscriptions.extend(subs['data'])
while subs.has_more:
  time.sleep(0.05) # rate limit
  starts_after = subs['data'][-1]['id']
  subs = stripe.Subscription.list(api_key=key, status='active', starting_after=starts_after)
  subscriptions.extend(subs['data'])
  

customers = []

for sub in subscriptions:
  product_codes = [i['plan']['product'] for i in sub['items']['data'] if i['plan']['product'] in catdrool_product_codes]
  if len(product_codes):
    cust_id = sub['customer']
    customer = stripe.Customer.retrieve(api_key=key, id=cust_id)
    customers.append(customer)
    time.sleep(0.05) # rate limit
    

shipping_records = []
filename = f'Catdrool-shipping-record_{date_str}.csv'
keys = []
for customer in customers:
  try:
    shipping_info = customer['shipping']['address']
    record = {
      'name': customer['shipping']['name'],
      'country': shipping_info['country'],
      'city': shipping_info['city'],
      'state': shipping_info['state'],
      'line_1': shipping_info['line1'],
      'line_2': shipping_info['line2'],
      'postal_code': shipping_info['postal_code']
    }
    if not keys:
      keys = record.keys()
    shipping_records.append(record)
  except Exception as e:
    print(f"failed on customer: {customer['id']}")
with open(filename, 'w') as f:
  writer = csv.DictWriter(f, fieldnames=keys)
  writer.writeheader()
  writer.writerows(shipping_records)

print(f"Records written to {filename}")




