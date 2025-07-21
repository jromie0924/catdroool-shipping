from http import HTTPStatus
import json
import logging
import requests
from common.singleton import Singleton
from config import config
from ratelimit import limits, sleep_and_retry
from services.authorization import Authorization
from services.crypt import Crypt


logger = logging.getLogger(config.APP_NAME)

class Domestics(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._auth = Authorization()
    self._crypt = Crypt()
    self._url = f"{config.USPS_URI}/addresses/v3/address"
    self._validated_address_cache = {}
    try:
      with open(config.VALIDATED_ADDRESSES_CACHE_FILE, 'rb') as f:
        encrypted_data = f.read()
        decrypted_json = self._crypt.decrypt_data(encrypted_data, self._crypt.get_key())
        self._validated_address_cache = json.loads(decrypted_json)
    except FileNotFoundError:
      logger.warning("Domestic validated address cache file not found. All address validation will be done via USPS.")
  
  def validate_address(self, address_1: str, address_2: str, city: str, state: str, zip: str) -> dict:
    if config.ADDRESS_VALIDATION_ENABLED:
      params = {
        "streetAddress": address_1,
        "secondaryAddress": address_2 or "",
        "city": city,
        "state": state,
        "ZIPCode": zip
      }
      key = f"{address_1}{address_2}{city}{state}{zip}"
      value = self._validated_address_cache.get(key)
      if value:
        return json.loads(value)
      return self._validate_address(params=params)
    return {}
    
  @sleep_and_retry
  @limits(calls=1, period=60) # limit to 1 call/minute - USPS limits to 60 calls/hour, so this keeps it within quota
  def _validate_address(self, params: dict) -> dict:
    headers = {
      "accept": "application/json",
      "authorization": f"bearer {self._auth.usps_token}"
    }
    
    zip = params["ZIPCode"][:5]
    plus_4 = params["ZIPCode"][6:]
    
    if plus_4:
      params['ZIPPlus4'] = plus_4
    response = requests.request("GET", url=self._url, headers=headers, params=params)
    if response.status_code == HTTPStatus.OK:
      payload: dict = response.json()
      address = payload.get("address")
      if not address:
        return {}
      key = "".join(list(params.values()))
      self._validated_address_cache[key] = json.dumps(address)
      return address
    return {}
  
  def save_validated_address_cache(self) -> None:
    encrypted_data = self._crypt.encrypt_data(json.dumps(self._validated_address_cache), self._crypt.get_key())
    with open(config.VALIDATED_ADDRESSES_CACHE_FILE, 'wb') as f:
      f.write(encrypted_data)
