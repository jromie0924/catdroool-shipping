from cryptography.fernet import Fernet
from common.singleton import Singleton
from config import config
from services.aws import Aws

class Crypt(Singleton):
  def __init__(self):
    if hasattr(self, '_initialized'):
      return None
    self._initialized = True
    self._aws = Aws()
    
  def generate_key(self):
    return Fernet.generate_key()
  
  def get_key(self) -> bytes:
    key = self._aws.get_secret(key=config.CRYPT_SECRET_NAME, type=bytes)
    if key:
      return key
    key = Fernet.generate_key()
    self._aws.put_secret(key=config.CRYPT_SECRET_NAME, value=key, type=bytes)
    return key
  
  def encrypt_data(self, data, key: bytes) -> bytes:
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data
  
  def decrypt_data(self, data: bytes, key: bytes):
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(data).decode()
    return decrypted_data