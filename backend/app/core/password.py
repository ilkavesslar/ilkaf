"""Password hashing service interface and Argon2id implementation.

Plaintext passwords are never stored or logged.
"""

from __future__ import annotations

from typing import Protocol

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError


class PasswordHasherError(Exception):
    """Raised when a password hashing operation fails."""


class PasswordHasherProtocol(Protocol):
    """Hash and verify passwords using a vetted algorithm."""

    def hash(self, plain_password: str) -> str: ...
    def verify(self, plain_password: str, hashed_password: str) -> bool: ...
    def needs_rehash(self, hashed_password: str) -> bool: ...


class Argon2idPasswordHasher:
    """Argon2id password hasher using the argon2-cffi library.

    The library generates salts automatically and applies reasonable defaults.
    """

    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, plain_password: str) -> str:
        if not isinstance(plain_password, str) or not plain_password:
            raise PasswordHasherError("password must be a non-empty string")
        try:
            return self._hasher.hash(plain_password)
        except Exception as exc:
            raise PasswordHasherError("password hashing failed") from exc

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        if not isinstance(plain_password, str) or not isinstance(
            hashed_password, str
        ):
            return False
        try:
            self._hasher.verify(hashed_password, plain_password)
        except VerificationError:
            return False
        except InvalidHash:
            return False
        return True

    def needs_rehash(self, hashed_password: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(hashed_password)
        except InvalidHash:
            return True


def get_password_hasher() -> PasswordHasherProtocol:
    """Return the configured password hasher."""
    return Argon2idPasswordHasher()
