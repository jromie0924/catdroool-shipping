import json
import os
import sys
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from services.emailer import Emailer
from models import emailType as EMAIL_TYPE


class MockConfig:
  APP_NAME = "test_app"
  EMAILS_ENABLED = True


@pytest.fixture
def mock_aws():
  mock = MagicMock()
  email_secrets = {
    "sender_email": "test@example.com",
    "sender_password": "test_password",
    "delivery_recipients": "delivery@example.com",
    "notification_recipients": "notification@example.com"
  }
  mock.get_secret.return_value = json.dumps(email_secrets)
  return mock


@pytest.fixture
def mock_smtp():
  mock = MagicMock()
  return mock


def test_emailer_init(mock_aws):
  """Test Emailer initialization"""
  # Clear singleton instances
  Emailer._instances = {}
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig):
    
    emailer = Emailer()
    
    assert emailer._sender_email == "test@example.com"
    assert emailer._sender_password == "test_password"
    assert emailer._delivery_recipients == "delivery@example.com"
    assert emailer._notification_recipients == "notification@example.com"


def test_emailer_singleton_behavior(mock_aws):
  """Test that Emailer follows singleton pattern"""
  # Clear singleton instances
  Emailer._instances = {}
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig):
    
    emailer1 = Emailer()
    emailer2 = Emailer()
    
    assert emailer1 is emailer2


def test_emailer_init_exception(mock_aws):
  """Test Emailer handles initialization exception gracefully"""
  # Clear singleton instances
  Emailer._instances = {}
  
  mock_aws.get_secret.side_effect = Exception("AWS Error")
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig):
    
    # Should not raise exception
    emailer = Emailer()


def test_send_email_delivery_type(mock_aws, mock_smtp):
  """Test sending a delivery email"""
  # Clear singleton instances
  Emailer._instances = {}
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig), \
       patch("services.emailer.smtplib.SMTP_SSL", return_value=mock_smtp):
    
    emailer = Emailer()
    emailer.send_email(
      body_html="<h1>Test Email</h1>",
      date_stamp="2024-03-15",
      subject="Test Subject",
      email_type=EMAIL_TYPE.DELIVERY
    )
    
    mock_smtp.ehlo.assert_called_once()
    mock_smtp.login.assert_called_once_with("test@example.com", "test_password")
    mock_smtp.sendmail.assert_called_once()
    mock_smtp.quit.assert_called_once()


def test_send_email_notification_type(mock_aws, mock_smtp):
  """Test sending a notification email"""
  # Clear singleton instances
  Emailer._instances = {}
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig), \
       patch("services.emailer.smtplib.SMTP_SSL", return_value=mock_smtp):
    
    emailer = Emailer()
    emailer.send_email(
      body_html="<h1>Notification</h1>",
      date_stamp="2024-03-15",
      subject="Notification",
      email_type=EMAIL_TYPE.NOTIFICATION
    )
    
    # Verify email was sent
    assert mock_smtp.sendmail.called


def test_send_email_with_attachments(mock_aws, mock_smtp):
  """Test sending an email with file attachments"""
  # Clear singleton instances
  Emailer._instances = {}
  
  file_content = b"test file content"
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig), \
       patch("services.emailer.smtplib.SMTP_SSL", return_value=mock_smtp), \
       patch("builtins.open", mock_open(read_data=file_content)):
    
    emailer = Emailer()
    files = [
      {"path": "/test/file1.csv", "name": "file1.csv"},
      {"path": "/test/file2.txt", "name": "file2.txt"}
    ]
    
    emailer.send_email(
      body_html="<h1>Test Email</h1>",
      files=files,
      date_stamp="2024-03-15",
      subject="Test Subject",
      email_type=EMAIL_TYPE.DELIVERY
    )
    
    assert mock_smtp.sendmail.called


def test_send_email_attachment_failure(mock_aws, mock_smtp):
  """Test that email sending continues even if attachment fails"""
  # Clear singleton instances
  Emailer._instances = {}
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig), \
       patch("services.emailer.smtplib.SMTP_SSL", return_value=mock_smtp), \
       patch("builtins.open", side_effect=FileNotFoundError):
    
    emailer = Emailer()
    files = [{"path": "/invalid/file.csv", "name": "file.csv"}]
    
    # Should not raise exception
    emailer.send_email(
      body_html="<h1>Test Email</h1>",
      files=files,
      date_stamp="2024-03-15",
      subject="Test Subject",
      email_type=EMAIL_TYPE.DELIVERY
    )
    
    # Email should still be sent even if attachment failed
    assert mock_smtp.sendmail.called


def test_send_email_disabled(mock_aws):
  """Test that email is not sent when EMAILS_ENABLED is False"""
  # Clear singleton instances
  Emailer._instances = {}
  
  mock_config = MockConfig()
  mock_config.EMAILS_ENABLED = False
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", mock_config), \
       patch("services.emailer.smtplib.SMTP_SSL") as mock_smtp_class:
    
    emailer = Emailer()
    emailer.send_email(
      body_html="<h1>Test Email</h1>",
      date_stamp="2024-03-15",
      subject="Test Subject",
      email_type=EMAIL_TYPE.DELIVERY
    )
    
    # SMTP should not be called when emails are disabled
    mock_smtp_class.assert_not_called()


def test_send_email_smtp_exception(mock_aws, mock_smtp):
  """Test that email sending handles SMTP exceptions gracefully"""
  # Clear singleton instances
  Emailer._instances = {}
  
  mock_smtp.sendmail.side_effect = Exception("SMTP Error")
  
  with patch("services.emailer.Aws", return_value=mock_aws), \
       patch("services.emailer.config", MockConfig), \
       patch("services.emailer.smtplib.SMTP_SSL", return_value=mock_smtp):
    
    emailer = Emailer()
    
    # Should not raise exception
    emailer.send_email(
      body_html="<h1>Test Email</h1>",
      date_stamp="2024-03-15",
      subject="Test Subject",
      email_type=EMAIL_TYPE.DELIVERY
    )
