import time
from typing import Union
from common.singleton import Singleton
from config import constants
from exceptions.cacheException import CacheException

class Cache(Singleton):
  def __init__(self):
    self._countries = {}
    self._country_states = {}
  
  def cache_country(self, country_code: str, country: dict):
    now = time.time() * 1000
    entry = {'data': country, constants.TIMESTAMP: now}
    self._countries[country_code] = entry
  
  def cache_country_states(self, country_code: str, states: list[dict]):
    now = time.time() * 1000
    entry = {"data": states, constants.TIMESTAMP: now}
    self._country_states[country_code] = entry
    
  def get_country(self, country_code) -> Union[dict, None]:
    try:
      entry = self._countries[country_code]
      if get_time_difference_hours(entry.get(constants.TIMESTAMP), time.now() * 1000) < constants.CACHE_TIMEOUT:
        return entry['data']
      
      # Cache entry has expired; remove it from cache.
      self._countries = {code: entry for code, entry in self._countries.items() if code != country_code}
    except KeyError as e:
      print(f'Country cache contains no key {country_code}.')
      
  def get_country_states(self, country_code) -> Union[list[dict], None]:
    try:
      entry = self._country_states[country_code]
      if get_time_difference_hours(entry.get(constants.TIMESTAMP), time.now() * 1000) < constants.CACHE_TIMEOUT:
        return entry['data']
      
      # Cache entry has expired; remove it from cache.
      self._country_states = {code: entry for code, entry in self._country_states if code != country_code}
    except KeyError:
      print(f'Country state cache contains no key {country_code}.')

    

def get_time_difference_hours(start: int, end: int):
  return float(end - start) / 1000.0 / 60.0 / 60.0