import hashlib
import hmac
import os

from fastapi import Request

SESSION_USER_KEY = "username"


class NotAuthenticated(Exception):
    """Raised by require_login; caught by an exception handler that redirects to /login."""


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, _, digest_hex = stored.partition("$")
    if not digest_hex:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, expected)


def require_login(request: Request) -> str:
    username = request.session.get(SESSION_USER_KEY)
    if not username:
        raise NotAuthenticated()
    return username
