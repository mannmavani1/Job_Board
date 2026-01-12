import logging
import time
from fastapi import FastAPI, Request
from sqlmodel import SQLModel, text
from app.database.db import engine
from app.routers.auth import router as auth_router
from app.routers.jobs import router as jobs_router
from app.routers.companies import router as companies_router
from app.routers.applications import router as applications_router
from app.routers.tag import router as tag_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Job Board API")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)   

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    start_time = time.time()
    
  
    logger.info(f"Incoming Request: {request.method} {request.url}")
    
    
    try:
        response = await call_next(request)
    except Exception as e:
       
        logger.error(f"Request failed: {e}")
        raise e
    
   
    process_time = time.time() - start_time
    
   
    logger.info(
        f"Completed: {response.status_code} "
        f"| Time: {process_time:.4f}s"
    )
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,      
    allow_methods=["*"],         
    allow_headers=["*"],        
)


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)