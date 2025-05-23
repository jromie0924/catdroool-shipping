import json
import requests
import logging
import time

from common.singleton import Singleton
from config import config
from http import HTTPStatus

from services.crypt import Crypt
from services.aws import Aws
import os

usps_url = "oauth2/v3/token"

logger = logging.getLogger(config.APP_NAME)

class Authorization(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._crypt = Crypt()
    self._aws = Aws()
    self._usps_api_token_cache = {}
    self._retrieve_credentials()
  
  def _retrieve_credentials(self):
    try:
      with open(config.API_TOKEN_CACHE_FILE, 'rb') as file:
        encrypted_data = file.read()
        key = self._crypt.get_key()
        data = json.loads(self._crypt.decrypt_data(encrypted_data, key))
        now = time.time() * 1000
        then = data.get("expiration")
        if then > now:
          self._usps_api_token_cache = data
        else:
          self._authenticate_usps()
    except FileNotFoundError:
      logging.info("No cache file found.")
      self._authenticate_usps()
    
  def _authenticate_usps(self):
    aws_secret_client = self._aws.secrets_client
  
    secrets = aws_secret_client.get_secret_value(SecretId='usps_api_credentials')
    if secrets:
      usps_secrets = json.loads(secrets.get("SecretString")) 
    
    headers = {
      "accept": "application/json"
    }
    payload = {
      "grant_type": "client_credentials",
      "scope": "addresses",
      "client_id": usps_secrets[config.USPS_CLIENT_ID],
      "client_secret": usps_secrets[config.USPS_CLIENT_SECRET]
    }
    try:
      response = requests.request("POST", f"{config.USPS_URI}/{usps_url}", headers=headers, data=payload)
      if response.status_code == HTTPStatus.OK:
        response_payload = response.json()
        access_token = response_payload['access_token']
        issued_at = response_payload['issued_at']
        expires_in = response_payload['expires_in'] * 1000 # convert to milliseconds
        
        '''
        subtract 10 minutes from the expiration window to go ahead and request another token if it's close to expiration
        This way we don't run as high a risk of the token expiring while the app is running.
        '''
        buffer = 10 * 60 * 1000 # 10 minutes converted to milliseconds.
        expires_in -= buffer
        
        
        self._usps_api_token_cache['token'] = access_token
        self._usps_api_token_cache['expiration'] = issued_at + expires_in
        logger.info(f"Successfully retrieved USPS access token. Expires in {'{:.2f}'.format(expires_in / 1000 / 60 / 60)} hours.")
        
        encrypted_data = self._crypt.encrypt_data(json.dumps(self._usps_api_token_cache), self._crypt.get_key())
        # Ensure the directory exists before writing the cache file
        os.makedirs(os.path.dirname(config.API_TOKEN_CACHE_FILE), exist_ok=True)
        with open(config.API_TOKEN_CACHE_FILE, 'wb') as file:
          file.write(encrypted_data)
        
    except KeyError as e:
      logger.error(f"Error with response payload of USPS API token retrieval.")
      raise e
    except Exception as e:
      logger.error(f"Failed to retrieve USPS API token.")
      raise e

  @property
  def usps_token(self):
    if not self._usps_api_token_cache:
      return None
    
    now = time.time() * 1000
    then = self._usps_api_token_cache.get('expiration')
    if now > then:
      # token has expired. Reacquire.
      try:
        self._authenticate_usps()
        return self._usps_api_token_cache.get('token')
      except Exception as e:
        logger.error("CRITICAL: cannot retrieve USPS API token.")
        return None
    return self._usps_api_token_cache.get('token')