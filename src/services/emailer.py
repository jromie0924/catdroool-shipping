import json
import logging
import smtplib

from common.singleton import Singleton
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import config
from models import emailType as EMAIL_TYPE
from services.aws import Aws
from email.mime.base import MIMEBase
from email import encoders


logger = logging.getLogger(config.APP_NAME)

class Emailer(Singleton):
  def __init__(self):
    if hasattr(self, "_initialized"):
      return None
    self._initialized = True
    self._aws = Aws()
    
    try:
      email_secrets: dict = json.loads(self._aws.get_secret(key="catdroool_email_secrets", type=str))
      self._sender_email: str = email_secrets.get("sender_email")
      self._sender_password: str = email_secrets.get("sender_password")
      self._delivery_recipients: str = email_secrets.get("delivery_recipients")
      self._notification_recipients: str = email_secrets.get("notification_recipients")
    except Exception as e:
      logger.error(f"Failed to retrieve email credentials and metadata: {e}")
    
  def send_email(self, body_html: str="", files: list[dict]=None, date_stamp="", subject="", email_type=EMAIL_TYPE.DELIVERY):
    if not config.EMAILS_ENABLED:
      return
    
    message = MIMEMultipart()
    message['From'] = self._sender_email
    if email_type == EMAIL_TYPE.DELIVERY:
      message['To'] = self._delivery_recipients
    elif email_type == EMAIL_TYPE.NOTIFICATION:
      message['To'] = self._notification_recipients
    message['Subject'] = f'{subject} {date_stamp}'
    
    
    message.attach(MIMEText(body_html, 'html'))
    if files:
      for file_info in files:
        file_path = file_info.get("path")
        file_name = file_info.get("name")
        if file_path and file_name:
          try:
            with open(file_path, "rb") as f:
              part = MIMEBase("application", "octet-stream")
              part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
              "Content-Disposition",
              f'attachment; filename="{file_name}"',
            )
            message.attach(part)
          except Exception as e:
            logger.error(f"Failed to attach file {file_name}: {e}")
    
    
    try:
      server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
      server.ehlo()
      server.login(self._sender_email, self._sender_password)
      
      text = message.as_string()
      server.sendmail(self._sender_email, message['To'].split(","), text)
      server.quit()
      logger.info(f"{email_type} email sent successfully")
      
    except Exception as e:
      logger.error(f"Error sending email: {e}")
  
  
if __name__ == '__main__':
  emailer = Emailer()
  emailer.send_email()