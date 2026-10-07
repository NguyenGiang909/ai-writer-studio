
import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

def _fernet() -> Fernet:
    if settings.environment != "development" and settings.secret_key == "dev-insecure-key-change-me":
        raise RuntimeError("SECRET_KEY must be set to a strong value outside development")
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))

def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()

def decrypt_secret(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()

def key_hint(secret: str) -> str:
    return "••••" + secret[-4:] if len(secret) >= 4 else "••••"

def public_credential_view(provider,key_hint,status="connected",base_url=None):
    return {"provider":provider,"key_hint":key_hint,"status":status,"secret":None,"base_url":base_url}
def resolve_model(task,task_override=None,project_override=None,account_default=None,system_fallback=None):
    return task_override or project_override or account_default or system_fallback
