"""Password hashing and JWT creation/validation.

Pure functions only — no database or Redis access here. Token *revocation*
state (which refresh tokens are still valid) lives in Redis and is handled
by the auth endpoints.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

ALGORITHM = "HS256"

# Argon2id — current OWASP recommendation; salts and parameters are encoded
# into the hash string itself, so verification needs no extra config.
_password_hash = PasswordHash.recommended()

# Verified against when a login email doesn't exist, so "unknown email" and
# "wrong password" take the same time — no account-enumeration timing oracle.
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing-equalization")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def create_token(
    *,
    user_id: uuid.UUID,
    role: str,
    token_type: TokenType,
    lifetime: timedelta,
    secret: str,
) -> tuple[str, str]:
    """Return (encoded_token, jti).

    The jti (unique token id) is what lets us revoke refresh tokens: Redis
    holds the set of still-valid refresh jtis, keyed with a TTL matching exp.
    """
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    claims = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), jti


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Validate signature and expiry; raises jwt.PyJWTError on any failure."""
    return jwt.decode(token, secret, algorithms=[ALGORITHM])
