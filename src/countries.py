import json
import requests
import time
from typing import Union
from http import HTTPStatus
from config import constants
from exceptions.cacheException import CacheException
from common.utils import get_time_difference_hours, Cache

class Countries:
  def __init__(self):
    with open('countries.json') as f:
      self._countries: dict = json.load(f)
      self._key = ''
      self._url = 'https://api.countrystatecity.in/v1/countries'
      self._headers = {
        'X-CSCAPI-KEY': self._key
      }
      self._cache = Cache()
      
      self._country_cache = {}
  
  def get_country_name(self, country_code: str) -> Union[str, None]:
    country: dict = self._cache.get_country(country_code=country_code)
    if country is not None:
      return country['name']
    else:
      try:
        response = requests.request("GET", f'{self._url}/{country_code}', headers=self._headers)
        if response.status_code == HTTPStatus.OK:
          country: dict = response.json()
          self._cache.cache_country(country_code=country_code, country=country)
          return country['name']
      except Exception:
        print(f'ERROR: failed to get country name for code {country_code}')


  def validate_state_code(self, country_code: str, state_code: str) -> bool:
    def filter_states(states):
      return [state for state in states if state['iso2'] == state_code]
    
    country_states = self._cache.get_country_states(country_code=country_code)
    if country_states is not None:
      results = filter_states(states)
      return len(results) == 1
    else:
      try:
        response = requests.request("GET", f'{self._url}/{country_code}/{state_code}')
        if response.status_code == HTTPStatus.OK:
          states = response.json()
          self._cache.cache_country_states(country_code=country_code, states=states)
          results = filter_states(states)
          return len(results) == 1
      except Exception:
        print(f'ERROR: failed to validate state code {state_code} for country code {country_code}')