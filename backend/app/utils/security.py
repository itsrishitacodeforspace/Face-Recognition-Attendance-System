from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
import logging
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()
BCRYPT_MAX_PASSWORD_BYTES = 72

# Security: Password hashing configuration
# - Scheme: bcrypt (cryptographically secure, resistant to brute force)
# - Rounds: 12 (increased complexity, slower hashing = better security)
# - Recommended: 12-16 rounds; larger values increase computation time and security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,
    deprecated="auto"
)


class TokenError(Exception):
    """Exception raised for token-related errors."""
    pass


def ensure_password_hashing_compatibility() -> None:
    """Validate passlib/bcrypt runtime compatibility before hashing passwords."""
    try:
        passlib_version = package_version("passlib")
        bcrypt_version = package_version("bcrypt")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "Password hashing dependencies are missing. Reinstall backend requirements."
        ) from exc

    try:
        bcrypt_major = int(bcrypt_version.split(".", 1)[0])
    except ValueError:
        bcrypt_major = None

    if passlib_version.startswith("1.7.") and bcrypt_major is not None and bcrypt_major >= 5:
        raise RuntimeError(
            "Incompatible password hashing dependencies detected: passlib 1.7.x "
            "requires bcrypt < 5. Install backend requirements to pin bcrypt==4.0.1."
        )


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hashed password
        
    Security:
    - Never store plain text passwords
    - Use proper password hashing (bcrypt, argon2, or scrypt)
    - Never log passwords or hashes
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password is too long for bcrypt: {len(password_bytes)} bytes "
            f"(max {BCRYPT_MAX_PASSWORD_BYTES})."
        )

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against its bcrypt hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password from database
        
    Returns:
        True if password matches, False otherwise
        
    Security:
    - Uses timing-attack-resistant comparison
    - Returns False for invalid hashes
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> tuple[str, datetime]:
    """
    Create a JWT access token.
    
    Args:
        subject: Subject claim (typically username or user ID)
        
    Returns:
        Tuple of (token, expiration_datetime)
        
    Security:
    - HS256 algorithm with strong secret key
    - Expiration time: configurable (default 30 minutes)
    - Includes token type to prevent misuse
    - Secret key must be changed in production
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), expire


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Subject claim (typically username or user ID)
        
    Returns:
        Tuple of (token, expiration_datetime)
        
    Security:
    - Longer expiration than access token (default 7 days)
    - Separate token type to prevent cross-token attacks
    - Should be rotated regularly
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), expire


def decode_token(token: str, expected_type: str = "access") -> str:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        expected_type: Expected token type ("access" or "refresh")
        
    Returns:
        Subject claim from token
        
    Raises:
        TokenError: If token is invalid or expired
        
    Security:
    - Validates token signature using secret key
    - Checks expiration date
    - Verifies token type matches expected type
    - Prevents JWT algorithm confusion attacks
    - No sensitive data logged (only warnings about validation failures)
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        token_type = payload.get("type")
        subject = payload.get("sub")
        if token_type != expected_type or not subject:
            raise TokenError("Invalid token payload")
        return str(subject)
    except JWTError as exc:
        # Security: Log only the error type, not the token or secret key
        logger.warning(f"Token decode failed: {type(exc).__name__}")
        raise TokenError("Invalid token") from exc
