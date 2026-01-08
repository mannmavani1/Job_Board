from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from uuid import UUID

from app.database.session import get_session
from app.models.user import User
from app.core.security import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()





def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = session.exec(
        select(User).where(User.id == int(user_id))
    ).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user
