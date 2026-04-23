import pytest

from app.utils.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    ensure_password_hashing_compatibility,
    hash_password,
    verify_password,
)


def test_hash_password_accepts_max_bcrypt_length() -> None:
    password = "a" * BCRYPT_MAX_PASSWORD_BYTES
    hashed = hash_password(password)

    assert isinstance(hashed, str)
    assert verify_password(password, hashed) is True


def test_hash_password_rejects_password_above_bcrypt_limit() -> None:
    password = "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1)

    with pytest.raises(ValueError, match="Password is too long for bcrypt"):
        hash_password(password)


def test_password_hashing_dependency_compatibility_check() -> None:
    ensure_password_hashing_compatibility()
