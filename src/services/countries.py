import json
from typing import Union
import os
import psycopg2

from common.singleton import Singleton
from config import config
from services.aws import Aws

class Countries(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._sql_path = 'sql'
    self._aws = Aws()
    self.get_sql_connection()
    
  def get_sql_connection(self):
    connection_fields: dict = json.loads(self._aws.get_secret(key=config.AWS_DB_SECRET_NAME, type=str))
    self._conn = psycopg2.connect(database = connection_fields.get('dbname'),
                                  user=connection_fields.get('username'),
                                  password=connection_fields.get('password'),
                                  host=connection_fields.get('host'),
                                  port=connection_fields.get('port'))
  
  def get_country_name_from_id(self, country_code: str) -> Union[str, None]:
    sql_file = os.path.join(self._sql_path, 'get_country_name_by_code.sql')
    if not os.path.isfile(sql_file):
      raise FileNotFoundError(f"SQL file not found: {sql_file}")
    with open(sql_file, 'r') as file:
      sql = file.read()
    
    cursor = self._conn.cursor()
    cursor.execute(sql, (country_code,))
    result = cursor.fetchone() # GRANT SELECT ON TABLE countries TO catdroool;
    cursor.close()
    return result[0] if result else None
  
  def get_state_code_by_country_code_state_code(self, country_code: str, state_code: str) -> str:
    if not state_code:
      raise ValueError("State code cannot be None or empty.")
    if len(state_code) > 2: # Covers the scenario where a state's name is provided rather than its actual code.
      return self.get_state_code_by_country_code_state_name(country_code=country_code, state_name=state_code)
    
    sql_file = os.path.join(self._sql_path, 'get_state_by_country_code_state_code.sql')
    if not os.path.isfile(sql_file):
      raise FileNotFoundError(f"SQL file not found: {sql_file}")
    
    with open(sql_file, 'r') as file:
      sql = file.read()
      
    cursor = self._conn.cursor()
    cursor.execute(sql, (country_code, state_code,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None
  
  def get_state_code_by_country_code_state_name(self, country_code: str, state_name: str) -> str:
    if not state_name:
      raise ValueError("State code cannot be None or empty.")
    sql_file = os.path.join(self._sql_path, 'get_state_by_country_code_state_code.sql')
    if not os.path.isfile(sql_file):
      raise FileNotFoundError(f"SQL file not found: {sql_file}")
    
    with open(sql_file, 'r') as file:
      sql = file.read()
      
    cursor = self._conn.cursor()
    cursor.execute(sql, (country_code, state_name,))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else None