import logging
import time
from fastapi import FastAPI, Request
from sqlmodel import SQLModel, text
from fastapi.middleware.cors import CORSMiddleware

# Database and Router Imports
from app.database.db import engine
from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.routers.companies import router as companies_router
from app.routers.applications import router as applications_router
from app.routers.tag import router as tag_router

"""
Application Entry Point.

This module initializes the FastAPI application, configures global middleware
(logging, CORS), sets up database tables on startup, and aggregates all API routers.
"""

# Initialize the Application
app = FastAPI(
    title="Job Board API",
    description="A production-ready REST API for a Job Board platform.",
    version="1.0.0"
)

# --- Logging Configuration ---
# Sets up the global logger to print info to the console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    """
    Global Middleware to log request details and execution time.

    **Purpose:**
    - Tracks every incoming request (Method + URL).
    - Measures how long the request took to process (latency).
    - Logs the final status code.
    - Catches and logs unhandled exceptions before re-raising them.
    """
    start_time = time.time()
    
    # Log the incoming request
    logger.info(f"Incoming Request: {request.method} {request.url}")
    
    try:
        # Process the request
        response = await call_next(request)
    except Exception as e:
        # Log critical errors that crash the endpoint
        logger.error(f"Request failed: {e}")
        raise e
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log the completion details
    logger.info(
        f"Completed: {response.status_code} "
        f"| Time: {process_time:.4f}s"
    )
    
    return response


# --- CORS Configuration ---
# Cross-Origin Resource Sharing (CORS) allows front-end applications 
# (e.g., React, Vue) hosted on different domains to communicate with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # In production, replace "*" with specific domains (e.g., ["https://my-frontend.com"])
    allow_credentials=True,      # Allow cookies/auth headers
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],         # Allow all headers
)


@app.on_event("startup")
def on_startup():
    """
    Application Startup Event.
    
    **Action:**
    - Connects to the database engine.
    - Creates all tables defined in SQLModel classes if they don't exist yet.
    """
    SQLModel.metadata.create_all(engine)


# --- System Health Checks ---

@app.get("/", tags=["Health"])
def health_check():
    """
    Simple health check endpoint.
    
    **Usage:**
    - Used by load balancers (e.g., AWS ELB, Render) to verify the service is running.
    """
    return {"status": "OK"}


@app.get("/db-check", tags=["Health"])
def db_check():
    """
    Database connectivity check.
    
    **Usage:**
    - Verifies that the application can actually execute queries against the database.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return {"database": "disconnected", "error": str(e)}


# --- Router Registration ---
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(companies_router)
app.include_router(applications_router)
app.include_router(tag_router)


if __name__ == "__main__":
    import uvicorn
    # Run the server programmatically (useful for debugging in IDEs)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


