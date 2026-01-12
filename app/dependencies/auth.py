from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database.session import get_session
from app.models.user import User
from app.core.security import decode_access_token

# Define the security scheme: Expects "Authorization: Bearer <token>"
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """
    FastAPI Dependency to authenticate and retrieve the current user.

    **Mechanism:**
    1. Extracts the Bearer Token from the 'Authorization' header.
    2. Decodes and validates the JWT signature.
    3. Extracts the 'sub' (User ID) from the token payload.
    4. Fetches the user from the database.
    5. Verifies that the user exists and is currently active.

    **Args:**
    - credentials (HTTPAuthorizationCredentials): The raw bearer token.
    - session (Session): Database session.

    **Returns:**
    - User: The authenticated user object.

    **Raises:**
    - 401 Unauthorized: If the token is invalid, expired, or the user is inactive.
    """
    
    try:
        # 1. Decode the token
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        # 2. Validate payload content
        if not user_id:
            raise ValueError("Token missing subject (user_id)")
            
    except Exception:
        # Catch any decoding errors (expired, signature mismatch, malformed)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Retrieve User from Database
    user = session.exec(
        select(User).where(User.id == int(user_id))
    ).first()

    # 4. Final Security Check: Ensure user exists and is not banned
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user