from http import HTTPStatus
from typing import Union
import requests
from common.singleton import Singleton
from config import config
from exceptions.addressNotFoundException import AddressNotFoundException
from services.authorization import Authorization


class Domestics(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._auth = Authorization()
    self._usps_token = self._auth.usps_token
    self._url = f"{config.USPS_URI}/addresses/v3/address"
    
  def validate_address(self, address_1: str, address_2: str, city: str, state: str, zip: str) -> Union[dict, None]:
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
        raise AddressNotFoundException(f"Address not found")
      return address
    
    raise AddressNotFoundException(f"Address not found")