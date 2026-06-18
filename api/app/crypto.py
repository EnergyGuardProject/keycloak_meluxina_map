"""Symmetric encryption helpers for slurm tokens.

Tokens are never stored in plaintext. They are encrypted with a Fernet key
(`ENCRYPTION_KEY`) before being written to the database and only decrypted in
memory when explicitly retrieved through an authenticated endpoint.
"""
from cryptography.fernet import Fernet

from .config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().encryption_key.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
