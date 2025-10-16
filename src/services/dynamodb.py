import logging

from boto3.dynamodb.conditions import Key
from common import utils
from common.singleton import Singleton
from config import config
from services.aws import Aws


logger = logging.getLogger(config.APP_NAME)

class DynamoDB(Singleton):
  def __init__(self):
    if hasattr(self, "_initialized"):
      return None
    self._initialized = True
    aws = Aws()
    self.dynamodb_resource = aws.dynamodb_client
  
  def put_item(self, item: dict={}, table_name: str=""):
    try:
      table = self.dynamodb_resource.Table(table_name)
      table.put_item(Item=item)
    except Exception:
      logger.error(f"Failed to insert data into DynamoDB table {table_name}. Item: {item}", exc_info=True)
  
  def get_latest_customer_metrics(self, table_name: str):
    table = self.dynamodb_resource.Table(table_name)
    condition_expression = Key(config.CATDROOOL_TRENDING_DYNAMO_PARTITION_KEY).eq(utils.get_previous_month())
    
    try:
      response: dict = table.query(KeyConditionExpression=condition_expression,
                        ScanIndexForward=False,
                        Limit=1)
      items = response.get("Items", [])
      return items[0] if items else None
    except Exception:
      logger.error(f"Error retrieving latest report metrics from database.", exc_info=True)
      return None
