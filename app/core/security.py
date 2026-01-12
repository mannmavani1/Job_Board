from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional
import bcrypt
from jose import jwt, JWTError

from app.core.config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

ALGORITHM = "HS256"


def prepare_password(password: str) -> bytes:
    """
    Sanitize and prepare a password for Bcrypt hashing.

    **Why this is needed:**
    - Bcrypt has a hard limit of 72 bytes for input strings.
    - If a user provides a password longer than 72 bytes, standard Bcrypt will 
      truncate it (ignoring everything after the 72nd byte) or raise an error.
    - To support long passwords safely, we pre-hash them using SHA-256 if they 
      exceed this limit. SHA-256 produces a fixed-length 64-character hex string, 
      which fits perfectly within Bcrypt's limit.

    **Args:**
    - password (str): The plain text password.

    **Returns:**
    - bytes: The password ready for final Bcrypt hashing.
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
    Securely hash a password using the Bcrypt algorithm.

    **Security features:**
    - Uses a random salt for every hash (preventing Rainbow Table attacks).
    - Uses an adaptive work factor (making brute-force expensive).

    **Args:**
    - password (str): The plain text password.

    **Returns:**
    - str: The hashed password string (safe for DB storage).
    """
    pwd_bytes = prepare_password(password)
    
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    
    # Return as string for database storage
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a submitted password against a stored hash.

    **Args:**
    - plain_password (str): The raw password input by the user.
    - hashed_password (str): The hash stored in the database.

    **Returns:**
    - bool: True if the password matches, False otherwise.
    """
    pwd_bytes = prepare_password(plain_password)
    hashed_bytes = hashed_password.encode("utf-8")
    
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a JSON Web Token (JWT) for authentication.

    **Mechanism:**
    - Encodes user data (claims) into a secure string.
    - Signs the token using the secret key to prevent tampering.
    - Sets an expiration time (`exp`) claim.

    **Args:**
    - data (dict): The payload to encode (e.g., `{"sub": "user_id"}`).
    - expires_delta (timedelta, optional): Custom expiration duration.

    **Returns:**
    - str: The encoded JWT string.
    """
    to_encode = data.copy()

    # Use timezone-aware UTC time
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    **Validation:**
    - Checks the signature using the `JWT_SECRET_KEY`.
    - Checks if the token has expired (`exp` claim).

    **Args:**
    - token (str): The encoded JWT string.

    **Returns:**
    - dict: The decoded payload (claims).

    **Raises:**
    - ValueError: If the token is invalid, tampered with, or expired.
    """
    try:
        return jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        raise ValueError("Invalid or expired token")