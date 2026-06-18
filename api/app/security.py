"""API-key authentication dependency.

Every endpoint requires a valid `X-API-Key` header. The comparison is
constant-time to avoid timing attacks.
"""
import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from .config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_header)) -> None:
    expected = get_settings().api_key
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key"
        )
