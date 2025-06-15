import logging
import os
import sys

from logging.handlers import RotatingFileHandler
from datetime import datetime as dt
from services.aws import Aws
from services.catdroool import Catdroool
from config import config

now = dt.now()

def _init_logger():
  logger = logging.getLogger(config.APP_NAME)
  logger.setLevel(config.LOGGING_LEVEL)
  
  now_str = now.strftime(config.DATE_FORMAT_STRING)
  log_file_path = f"{config.LOG_FILE_LOCATION}/{now_str}/catdroool.log"
  
  # Create log directory if it doesn't exist
  dir = os.path.dirname(log_file_path)
  os.makedirs(dir, exist_ok=True)
  
  # Log formatter
  formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

  # Stream handler (sys.stdout) for console output
  stream_handler = logging.StreamHandler(sys.stdout)
  stream_handler.setFormatter(formatter)
  
  # Rotating file handler
  # Will keep 2 files, each with a max size of 1MB
  # When the log file reaches 1MB, it will create a new log file
  # The oldest log file will be deleted
  file_handler = RotatingFileHandler(log_file_path, mode='a', maxBytes=1024*1024*10, backupCount=1)
  file_handler.setFormatter(formatter)
  
  # Add handlers to the logger
  logger.addHandler(file_handler)
  logger.addHandler(stream_handler)

if __name__ == '__main__':
  _init_logger()
  logger = logging.getLogger(config.APP_NAME)
  try:
    aws_secret_loc = sys.argv[1]
    aws = Aws(aws_secret_loc)
  except KeyError as e:
    logger.error(f"Error: {e}")
    sys.exit(1)
  
  catdroool = Catdroool(now=now)
  catdroool.generate_report()