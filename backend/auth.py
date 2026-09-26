"""
JWT issuing and verification.

Deliberately dependency-free: HMAC-SHA256 over a compact token is a few lines
of stdlib, so this does not justify pulling in a crypto library.

Why it exists: the app previously had no tokens at all. Login returned a bare
user_id which the client stored in localStorage and sent as a bearer token
that no route ever checked, so any /patient-details/{user_id} guess exposed
another patient's records.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import Config

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_SECONDS = 60 * 60  # 1 hour


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str) -> str:
    return _b64encode(
        hmac.new(Config.JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    )


def create_access_token(user_id: int) -> str:
    """
    Issue a signed access token carrying the user id and an expiry.

    The subject is the only claim. Role and patient claims would be added here
    if the app ever needed authorization distinct from authentication.
    """
    header = _b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload = _b64encode(
        json.dumps(
            {"sub": str(user_id), "exp": int(time.time()) + ACCESS_TOKEN_TTL_SECONDS}
        ).encode()
    )
    message = f"{header}.{payload}"
    return f"{message}.{_sign(message)}"


def decode_access_token(token: str) -> int:
    """
    Verify a token's signature and expiry, and return its user id.

    Raises:
        HTTPException 401 if the token is malformed, unsigned, tampered with,
            or expired. Every failure returns the same message so an attacker
            cannot tell a forged token from an expired one.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    parts = token.split(".")
    if len(parts) != 3:
        raise unauthorized

    header, payload, signature = parts
    expected = _sign(f"{header}.{payload}")
    # Constant-time compare so token forgery cannot be timed character by character.
    if not hmac.compare_digest(signature, expected):
        raise unauthorized

    try:
        claims = json.loads(_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        raise unauthorized

    if int(claims.get("exp", 0)) < int(time.time()):
        raise unauthorized

    return int(claims["sub"])


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """FastAPI dependency resolving a bearer token to a user id."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)