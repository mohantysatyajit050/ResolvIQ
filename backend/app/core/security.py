from pwdlib import PasswordHash

# recommended() = Argon2, with safe default settings
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Turn a plain password into a salted Argon2 hash."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a typed password against a stored hash (used by login on Day 4)."""
    return _password_hash.verify(password, password_hash)
