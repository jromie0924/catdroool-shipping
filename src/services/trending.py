import xlsxwriter as excel

from common.singleton import Singleton
from datetime import datetime as dt
from config import config
from services.dynamodb import DynamoDB


CUSTOMER_COUNT_DOMESTIC_KEY = "domestic_customer_count"
CUSTOMER_COUNT_INTL_KEY = "international_customer_count"
CUSTOMER_COUNT_TOTAL_KEY = "total_customer_count"


class Trending(Singleton):
  def __init__(self):
    if hasattr(self, "_initialized"):
      return None
    self._dynamodb = DynamoDB()
    
  def build_trending_item(self, cust_dom: int, cust_intl: int) -> dict:
    now = dt.now()
    timestamp = round(now.timestamp())
    return {
      "timestamp": timestamp,
      "year": now.year,
      "month": now.month,
      "day": now.day,
      CUSTOMER_COUNT_DOMESTIC_KEY: cust_dom,
      CUSTOMER_COUNT_INTL_KEY: cust_intl,
      CUSTOMER_COUNT_TOTAL_KEY: cust_dom + cust_intl,
    }
    
  @staticmethod
  def compare_items(this_item: dict, that_item: dict) -> dict:
    domestic_this = this_item.get(CUSTOMER_COUNT_DOMESTIC_KEY)
    domestic_that = that_item.get(CUSTOMER_COUNT_DOMESTIC_KEY)
    domestic_diff = domestic_this - domestic_that
    domestic_perc = round(domestic_diff / domestic_that * 100, 1)
    
    intl_this = this_item.get(CUSTOMER_COUNT_INTL_KEY)
    intl_that = that_item.get(CUSTOMER_COUNT_INTL_KEY)
    intl_diff = intl_this - intl_that
    intl_perc = round(intl_diff / intl_that * 100, 1)
    
    total_this = this_item.get(CUSTOMER_COUNT_TOTAL_KEY)
    total_that = that_item.get(CUSTOMER_COUNT_TOTAL_KEY)
    total_diff = total_this - total_that
    total_perc = round(total_diff / total_that * 100, 1)
    
    comparison_obj = {
      "domestic": {
        "current_count": domestic_this,
        "diff": f"{domestic_diff}",
        "perc": f"{domestic_perc}%"
      },
      "intl": {
        "current_count": intl_this,
        "diff": f"{intl_diff}",
        "perc": f"{intl_perc}%"
      },
      "total": {
        "current_count": total_this,
        "diff": f"{total_diff}",
        "perc": f"{total_perc}%"
      }
    }
    
    return comparison_obj
    
  def analyze_customer_counts(self, customers_domestic: list[dict], customers_intl: list[dict]):
    item = self.build_trending_item(cust_dom=len(customers_domestic),
                                    cust_intl=len(customers_intl))
    previous_item = self._dynamodb.get_latest_customer_metrics(config.CATDROOOL_TRENDING_DYNAMODB_TABLE)
    
    self._dynamodb.put_item(item=item, table_name=config.CATDROOOL_TRENDING_DYNAMODB_TABLE)
    
    return Trending.compare_items(item, previous_item or item)
  
  @staticmethod
  def build_metrics_comparison_report(filename, comparison_obj: dict):
    workbook = excel.Workbook(filename)
    for key in comparison_obj.keys():
      sheet = workbook.add_worksheet(key)
      sheet.write(0, 0, "Current Count")
      sheet.write(0, 1, "Difference From Last Month")
      sheet.write(0, 2, "Percentage Difference From Last Month")
      item: dict = comparison_obj.get(key)
      for idx, val in enumerate(item.values()):
        sheet.write(1, idx, val)
    workbook.close()