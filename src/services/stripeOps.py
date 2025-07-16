import json
import logging
import stripe

from ratelimit import limits, sleep_and_retry
from stripe import ListObject, Subscription
from common.singleton import Singleton
from config import config
from services.aws import Aws


logger = logging.getLogger(config.APP_NAME)

class StripeOps(Singleton):
  def __init__(self):
    if not hasattr(self, "_initialized"):
      return None
    self._initialized = True
    self._aws = Aws()
    key_dict = json.loads(self._aws.get_secret(key=config.STRIPE_SECRET_KEY, type=str))
    self._stripe_api_key = key_dict.get(config.STRIPE_SECRET_KEY)
    self._retrieve_catdroool_products()
    
  def _retrieve_catdroool_products(self):
    logging.info("Retrieving all catdroool product codes")
    all_products = stripe.Product.search(api_key=self._stripe_api_key, query=f"name~'{config.PRODUCT_FILTER}'")
    self._domestic_products = [p.get('id') for p in all_products if config.INTERNATIONAL_FILTER.lower() not in p.get('name').lower()]
    self._intl_products = [p.get('id') for p in all_products if config.INTERNATIONAL_FILTER.lower() in p.get('name').lower()]
    product_code_count = len(self._domestic_products) + len(self._intl_products)
    logging.info(f"Retrieved {product_code_count} products.")
  
  @sleep_and_retry
  @limits(calls=config.STRIPE_CALLS_PER_SECOND, period=config.STRIPE_SECONDS)
  def _get_subscriptions_page(self, starting_after=None) -> ListObject[Subscription]:
    return Subscription.list(api_key=self._stripe_api_key, starting_after=starting_after)
  
  def get_all_subscriptions(self) -> list[dict]:
    logger.info("Getting all subscriptions.")
    subscriptions: list[dict] = []
    page: ListObject[Subscription] = self._get_subscriptions_page()
    if page.get('data'):
      subscriptions.extend(page.get('data'))
    while page.has_more:
      starting_after = page.get('data')[-1]['id']
      page = self._get_subscriptions_page(starting_after=starting_after)
      if page.get('data'):
        subscriptions.extend(page.get('data'))
    return subscriptions
  
  
  def filter_subs_on_catdroool_products(self, subscriptions: list[dict]) -> list[dict]:
    def map_function(subscription: dict) -> dict:
      subscription['items']['data'] = [item for item in subscription['items']['data'] if item['plan']['product'] in [*self._domestic_products, *self._intl_products]]
      return subscription
    subscriptions = map(lambda subscription: map_function(subscription), subscriptions)
    return subscriptions
  
  # TODO: retrieve invoices - see temp-files/test.py