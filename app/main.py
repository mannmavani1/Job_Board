from fastapi import FastAPI
from sqlmodel import text
from app.database.db import engine

app = FastAPI(title="Job Board API")

@app.get("/health")
def health_check():
    return {"status": "OK"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}
