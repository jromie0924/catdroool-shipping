import logging

from botocore.exceptions import BotoCoreError, ClientError
from common.singleton import Singleton
from config import config
from services.aws import Aws


logger = logging.getLogger(config.APP_NAME)

class S3(Singleton):
  def __init__(self):
    self._client = Aws().s3_client
    self._bucket = config.REPORT_BUCKET

  def upload_report_files(self, files: list[dict], prefix: str) -> list[str]:
    if not self._bucket:
      logger.info("No report bucket configured; reports stored locally.")
      return []

    uploaded: list[str] = []
    for file_info in files:
      key = f"{prefix}/{file_info['name']}"
      try:
        self._client.upload_file(file_info['path'], self._bucket, key)
        uploaded.append(key)
      except (BotoCoreError, ClientError, OSError) as e:
        logger.error(f"Failed to upload {file_info['name']} to s3://{self._bucket}/{key}: {e}")

    logger.info(f"Archived {len(uploaded)}/{len(files)} report files to s3://{self._bucket}/{prefix}/")
    return uploaded
