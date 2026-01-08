from sqlmodel import create_engine
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=True,           # Logs SQL queries (disable in prod)
    pool_pre_ping=True   # Ensures dead connections are recycled
)
