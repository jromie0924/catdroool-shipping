import logging

from botocore.exceptions import BotoCoreError, ClientError
from common.singleton import Singleton
from config import config
from services.aws import Aws


logger = logging.getLogger(config.APP_NAME)

class S3(Singleton):
  def __init__(self):
    if hasattr(self, "_initialized"):
      return None
    self._initialized = True
    self._client = Aws().s3_client
    self._bucket = config.REPORT_BUCKET

  def upload_report_files(self, files: list[dict], prefix: str) -> list[str]:
    """
    Archive the generated reports, returning the keys that landed.

    A failed upload is logged rather than raised: in production the email is still the
    primary delivery mechanism and losing the archive should not lose the report. On a dev
    stack, where email is off, the errors below are the only signal that a run produced
    nothing, so the summary line always reports how many of the files made it.
    """
    if not self._bucket:
      logger.info("No report bucket configured; the report stays on the task's local disk.")
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
