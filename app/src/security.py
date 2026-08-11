import base64
import binascii
import hashlib
import hmac
import os
import secrets
import time
from uuid import UUID

from .exceptions import AuthenticationError


PASSWORD_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, saved_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = saved_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual_hash, expected_hash)


def create_access_token(user_id: UUID) -> str:
    lifetime = int(os.getenv("AUTH_TOKEN_TTL_MINUTES", "1440"))
    payload = f"{user_id}:{int(time.time()) + lifetime * 60}"
    signature = hmac.new(_auth_secret(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
    return token.rstrip("=")


def get_user_id_from_token(token: str) -> UUID:
    try:
        padding = "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(token + padding).decode()
        user_id, expires_at, signature = decoded.split(":")
        payload = f"{user_id}:{expires_at}"
        expected_signature = hmac.new(
            _auth_secret(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationError("Недействительный токен")
        if int(expires_at) < time.time():
            raise AuthenticationError("Срок действия токена истёк")
        return UUID(user_id)
    except AuthenticationError:
        raise
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise AuthenticationError("Недействительный токен") from None


def _auth_secret() -> bytes:
    return os.getenv("AUTH_SECRET", "development-secret").encode()
