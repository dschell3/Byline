"""Password hashing for sign-in (SCRUM-9).

Argon2id, the memory-hard algorithm OWASP recommends first. Hashes carry
their own parameters, so the cost can be raised later without a migration:
``needs_rehash`` reports when a stored hash is below the current settings.

The dummy hash exists so an unknown email costs the same time as a wrong
password. ``verify_password`` always runs a real verification, even when
there is no account, which is what keeps response timing from revealing
whether an email is registered.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# Hashed once at import. Verifying any password against it fails, but it
# takes exactly as long as verifying against a real account's hash.
_DUMMY_HASH = _hasher.hash("dummy-password-never-matches")


def hash_password(password: str) -> str:
    """Return an Argon2id hash suitable for ``person.password_hash``."""
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    """True only if ``password`` matches ``stored_hash``.

    Pass ``None`` when no account was found: the check still runs, against
    the dummy hash, so the caller's timing is the same on both paths.
    """
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True when the stored hash was made with weaker parameters than today's."""
    return _hasher.check_needs_rehash(stored_hash)
