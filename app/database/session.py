from sqlmodel import Session
from app.database.db import engine
from typing import Generator

def get_session() -> Generator[Session, None, None]:
    """
    FastAPI Dependency for database sessions.

    **Pattern:**
    - Creates a new `Session` for each incoming request.
    - Uses `yield` to provide the session to the path operation.
    - Automatically closes the session after the request is finished (even if an error occurs).

    **Usage:**
    `def my_endpoint(session: Session = Depends(get_session)):`

    **Returns:**
    - Generator[Session]: A generator that yields a database session.
    """
    with Session(engine) as session:
        yield session