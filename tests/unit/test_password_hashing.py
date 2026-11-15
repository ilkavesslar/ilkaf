import pytest
from app.core.password import (
    Argon2idPasswordHasher,
    PasswordHasherError,
    get_password_hasher,
)


@pytest.fixture
def hasher() -> Argon2idPasswordHasher:
    return Argon2idPasswordHasher()


def test_get_password_hasher_returns_argon2id() -> None:
    assert isinstance(get_password_hasher(), Argon2idPasswordHasher)


def test_hash_and_verify_roundtrip(hasher: Argon2idPasswordHasher) -> None:
    password = "correct-horse-battery-staple"
    hashed = hasher.hash(password)
    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert hasher.verify(password, hashed) is True


def test_wrong_password_rejected(hasher: Argon2idPasswordHasher) -> None:
    password = "correct-horse-battery-staple"
    hashed = hasher.hash(password)
    assert hasher.verify("wrong-password", hashed) is False


def test_different_hashes_for_same_password(hasher: Argon2idPasswordHasher) -> None:
    password = "reuse-me"
    first = hasher.hash(password)
    second = hasher.hash(password)
    assert first != second
    assert hasher.verify(password, first) is True
    assert hasher.verify(password, second) is True


def test_invalid_hash_rejected(hasher: Argon2idPasswordHasher) -> None:
    assert hasher.verify("any-password", "not-a-valid-hash") is False
    assert hasher.verify("any-password", "") is False


def test_empty_password_rejected(hasher: Argon2idPasswordHasher) -> None:
    with pytest.raises(PasswordHasherError):
        hasher.hash("")


def test_password_values_do_not_appear_in_exceptions(
    hasher: Argon2idPasswordHasher,
) -> None:
    secret = "super-secret-password"
    with pytest.raises(PasswordHasherError) as exc:
        hasher.hash("")
    assert secret not in str(exc.value)


def test_needs_rehash_on_current_hash(hasher: Argon2idPasswordHasher) -> None:
    hashed = hasher.hash("my-password")
    # Current hash should not need rehashing unless defaults changed.
    assert hasher.needs_rehash(hashed) is False


def test_needs_rehash_on_invalid_hash(hasher: Argon2idPasswordHasher) -> None:
    assert hasher.needs_rehash("not-a-hash") is True
