import stripe

from exceptions.noApiKeyException import NoApiKeyException


class StripeService:
  def __init__(self):
    # TODO: Add boto3 as a dependency
    # TODO: Need to (likely) create a role that can be assumed by the application to access the AWS account
    self._api_key: str = '' # TODO: replace with boto call to get from secrets
    pass

  def get_customer(self, customer_id: str) -> dict:
    #TODO
    pass
    
  def search_products(self, query) -> dict:
    return stripe.Product.search(api_key=self._api_key, query=query)