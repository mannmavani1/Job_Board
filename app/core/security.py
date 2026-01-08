from datetime import datetime, timedelta
import hashlib
from typing import Optional
import bcrypt
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def prepare_password(password: str) -> bytes:
    """
    Prepares a password for bcrypt hashing.
    
    Bcrypt has a limit of 72 bytes. If a password is longer than this,
    we hash it with SHA-256 first to get a 64-character (bytes) hex digest,
    which fits safely inside bcrypt's limit.
    """
    password_bytes = password.encode("utf-8")
    
    if len(password_bytes) > 72:
        # Pre-hash long passwords to ensure they fit in bcrypt limits
        # hexdigest() returns 64 chars, which is < 72 bytes
        hash_object = hashlib.sha256(password_bytes)
        return hash_object.hexdigest().encode("utf-8")
        
    return password_bytes

def get_password_hash(password: str) -> str:
    """
    Hashes a password using a random salt and the bcrypt algorithm.
    """
    pwd_bytes = prepare_password(password)
    
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    
    # Return as string for database storage
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a stored hash.
    """
    pwd_bytes = prepare_password(plain_password)
    hashed_bytes = hashed_password.encode("utf-8")
    
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        raise ValueError("Invalid or expired token")
