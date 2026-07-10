import logging
import boto3

from common.singleton import Singleton
from config import config

logger = logging.getLogger(config.APP_NAME)

class Aws(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._region = config.AWS_REGION

  # boto3 resolves credentials on its own: the ECS task role in Fargate (via the endpoint
  # named by AWS_CONTAINER_CREDENTIALS_RELATIVE_URI), and whatever is in the environment
  # or ~/.aws/credentials when run locally. Nothing here should ever hold a long-lived key.
  @property
  def secrets_client(self):
    return boto3.client('secretsmanager', region_name=self._region)

  @property
  def dynamodb_resource(self):
    return boto3.resource('dynamodb', region_name=self._region)

  @property
  def s3_client(self):
    return boto3.client('s3', region_name=self._region)

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
