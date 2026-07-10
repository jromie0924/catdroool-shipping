import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.s3 import S3


class MockConfig:
  APP_NAME = "test_app"
  REPORT_BUCKET = "catdroool-reports-test"


class MockConfigNoBucket:
  APP_NAME = "test_app"
  REPORT_BUCKET = ""


@pytest.fixture(autouse=True)
def clear_singleton():
  S3._instances = {}
  yield
  S3._instances = {}


@pytest.fixture
def mock_aws():
  mock = MagicMock()
  mock.s3_client = MagicMock()
  return mock


@pytest.fixture
def files():
  return [
    {"name": "domestic.csv", "path": "output/2026-07-09/domestic.csv"},
    {"name": "errors.csv", "path": "output/2026-07-09/errors.csv"},
  ]


def build_s3(mock_aws, config=MockConfig):
  with patch("services.s3.Aws", return_value=mock_aws), \
       patch("services.s3.config", config):
    return S3()


def test_uploads_each_file_under_the_date_prefix(mock_aws, files):
  s3 = build_s3(mock_aws)

  with patch("services.s3.config", MockConfig):
    uploaded = s3.upload_report_files(files=files, prefix="2026-07-09")

  assert uploaded == ["2026-07-09/domestic.csv", "2026-07-09/errors.csv"]
  mock_aws.s3_client.upload_file.assert_has_calls([
    call("output/2026-07-09/domestic.csv", "catdroool-reports-test", "2026-07-09/domestic.csv"),
    call("output/2026-07-09/errors.csv", "catdroool-reports-test", "2026-07-09/errors.csv"),
  ])


def test_upload_is_skipped_when_no_bucket_is_configured(mock_aws, files):
  s3 = build_s3(mock_aws, config=MockConfigNoBucket)

  with patch("services.s3.config", MockConfigNoBucket):
    uploaded = s3.upload_report_files(files=files, prefix="2026-07-09")

  assert uploaded == []
  mock_aws.s3_client.upload_file.assert_not_called()


def test_a_failed_upload_does_not_stop_the_remaining_files(mock_aws, files):
  error = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
  mock_aws.s3_client.upload_file.side_effect = [error, None]

  s3 = build_s3(mock_aws)
  with patch("services.s3.config", MockConfig):
    uploaded = s3.upload_report_files(files=files, prefix="2026-07-09")

  # The report still reaches the delivery recipients by email, so one bad key must not
  # abort the archive of the others.
  assert uploaded == ["2026-07-09/errors.csv"]
  assert mock_aws.s3_client.upload_file.call_count == 2


def test_a_missing_local_file_is_logged_and_skipped(mock_aws, files):
  mock_aws.s3_client.upload_file.side_effect = [OSError("no such file"), None]

  s3 = build_s3(mock_aws)
  with patch("services.s3.config", MockConfig):
    uploaded = s3.upload_report_files(files=files, prefix="2026-07-09")

  assert uploaded == ["2026-07-09/errors.csv"]


def test_upload_report_files_with_no_files(mock_aws):
  s3 = build_s3(mock_aws)

  with patch("services.s3.config", MockConfig):
    assert s3.upload_report_files(files=[], prefix="2026-07-09") == []

  mock_aws.s3_client.upload_file.assert_not_called()
