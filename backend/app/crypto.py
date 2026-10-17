"""Field-level encryption for sensitive free text (symptoms, documents, life stories, messages)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from .config import settings


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.data_key.encode()).digest()))


class EncryptedText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else "enc:" + _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None or not value.startswith("enc:"):
            return value
        try:
            return _fernet().decrypt(value[4:].encode()).decode()
        except InvalidToken:
            return "[unreadable: wrong DATA_KEY]"
