from http import HTTPStatus
import logging
import requests
from common.singleton import Singleton
from config import config
from ratelimit import limits, sleep_and_retry
from services.authorization import Authorization


logger = logging.getLogger(config.APP_NAME)

class Domestics(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._auth = Authorization()
    self._usps_token = self._auth.usps_token
    self._url = f"{config.USPS_URI}/addresses/v3/address"
  
  def validate_address(self, address_1: str, address_2: str, city: str, state: str, zip: str) -> dict:
    if config.ADDRESS_VALIDATION_ENABLED:
      return self._validate_address(address_1=address_1, address_2=address_2, city=city, state=state, zip=zip)
    return {}
    
  @sleep_and_retry
  @limits(calls=1, period=60) # limit to 1 call/minute - USPS limits to 60 calls/hour, so this keeps it within quota
  def _validate_address(self, address_1: str, address_2: str, city: str, state: str, zip: str) -> dict:
    headers = {
      "accept": "application/json",
      "authorization": f"bearer {self._usps_token}"
    }
    
    zip = zip[:5]
    plus_4 = zip[6:]
    
    params = {
      "streetAddress": address_1,
      "secondaryAddress": address_2,
      "city": city,
      "state": state,
      "ZIPCode": zip
    }
    if plus_4:
      params['ZIPPlus4'] = plus_4
    response = requests.request("GET", url=self._url, headers=headers, params=params)
    if response.status_code == HTTPStatus.OK:
      payload: dict = response.json()
      address = payload.get("address")
      if not address:
        return {}
      return address
    
    return {}