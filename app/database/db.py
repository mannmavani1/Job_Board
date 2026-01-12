from sqlmodel import create_engine
from app.core.config import DATABASE_URL

"""
Database Configuration Module.

This module initializes the SQLAlchemy engine, which is the core interface 
to the database. It handles connection pooling and dialect execution.
"""

# Initialize the Database Engine
# This object is global and will be shared across all sessions.
engine = create_engine(
    DATABASE_URL,
    
    # pool_pre_ping=True:
    # Before returning a connection from the pool, the engine will emit a 
    # simple "SELECT 1" to ensure the database is still responsive.
    # This prevents "OperationalError: server closed the connection unexpectedly"
    # which often happens on cloud databases (like Render) after periods of inactivity.
    pool_pre_ping=True
)