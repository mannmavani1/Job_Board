import os
from dotenv import load_dotenv

"""
Configuration Settings Module.

This module is responsible for loading environment variables and making them 
accessible throughout the application. It handles:
1. Loading variables from a local `.env` file (for development).
2. Normalizing Database URLs (fixing dialect prefixes).
3. Validating that critical secrets exist before the app starts.
"""

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Database Configuration ---
# Render and other PaaS providers often provide the URL starting with 'postgres://'
# However, SQLAlchemy requires 'postgresql://' to identify the correct driver.
DATABASE_URL = os.getenv("DB_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# --- Security Configuration ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# --- Critical Validation ---
# We raise errors immediately if essential secrets are missing.
# This prevents the application from starting in a broken state.

if not DATABASE_URL:
    raise ValueError("CRITICAL ERROR: 'DB_URL' environment variable is not set.")

if not JWT_SECRET_KEY:
    raise ValueError("CRITICAL ERROR: 'JWT_SECRET_KEY' environment variable is not set.")