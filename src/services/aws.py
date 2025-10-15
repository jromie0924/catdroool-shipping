import logging
import csv
import boto3

from common.singleton import Singleton
from config import config

logger = logging.getLogger(config.APP_NAME)

class Aws(Singleton):
  def __init__(self, aws_secret_loc: str=""):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._region = config.AWS_REGION
    aws_access_file = f"{aws_secret_loc}/{config.AWS_ACCESS_KEY_FILENAME}"
    try:
      with open(aws_access_file, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        if header != [config.AWS_ACCESS_KEY_ID_NAME, config.AWS_SECRET_ACCESS_KEY_NAME]:
          raise Exception("Failed to load aws access key file")
        row = next(reader)
        self._access_key: str = row[0]
        self._secret_key: str = row[1]
    except FileNotFoundError as e:
      logger.error("Failed to load aws access key file")
      raise e
    
  @property
  def secrets_client(self):
    if self._access_key and self._secret_key:
      return boto3.client('secretsmanager',
                            aws_access_key_id=self._access_key,
                            aws_secret_access_key=self._secret_key,
                            region_name=self._region)
      
  @property
  def dynamodb_client(self):
    if self._access_key and self._secret_key:
      return boto3.client('dynamodb',
                          aws_access_key_id=self._access_key,
                          aws_secret_access_key=self._secret_key,
                          region_name=self._region)

  def get_secret(self, key: str, type: type):
    client = self.secrets_client
    try:
      response = client.get_secret_value(SecretId=key)
      if type == str:
        return response.get("SecretString")
      elif type == bytes:
        return response.get("SecretBinary")
    except Exception:
      logger.error(f"Failed to retrieve secret {key} from AWS.")
      
  def put_secret(self, key: str, value, type: type):
    client = self.secrets_client
    try:
      response = None
      if type == bytes:
        response = client.create_secret(Name=key,
                                        SecretBinary=value)
      elif type == str:
        response = client.create_secret(Name=key,
                                        SecretString=value)
      if response:
        logger.info(f"Successfully uploaded secret \"{key}\"")
      else:
        logger.error(f"Failed to uplaod secret \"{key}\"")
    except Exception as e:
      logger.error(f"An error occurred when trying to contact AWS: {e}")

      
"""

{'id': {'S': '659019a5-ea0b-43bc-a8cc-cde221ecf90e'}, 'report_timestamp': {'S': '251014T213739'}, 'year': {'N': '2025'}, 'month': {'N': '10'}, 'day': {'N': '14'}, 'total_customers': {'N': '570'}, 'domestic_customers': {'N': '530'}, 'international_customers': {'N': '40'}}

schema:
  id: str (P-key)
  report_timestamp: full timestamp (str)
  domestic_customer_count: int
  international_customer_count: int
  total_customers: int
  year: int (sort key)
  day: int

"""