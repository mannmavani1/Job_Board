from fastapi import FastAPI
from sqlmodel import SQLModel, text
from app.database.db import engine
from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.routers.companies import router as companies_router
from app.routers.applications import router as applications_router
from app.routers.tag import router as tag_router


app = FastAPI(title="Job Board API")

@app.on_event("startup")
def on_startup():
    """Creates database tables when the app starts"""
    SQLModel.metadata.create_all(engine)

@app.get("/health")
def health_check():
    return {"status": "OK"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}


app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(companies_router)
app.include_router(applications_router)
app.include_router(tag_router)
