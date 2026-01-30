from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
try:
    from langchain.chains import RetrievalQA
except ImportError:
    from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate  
from langchain_core.prompts import ChatPromptTemplate 
from langchain_core.tools import Tool
from langchain.agents import create_tool_calling_agent, AgentExecutor #

from app.database.session import get_session
from app.ai.llm import get_llm
from app.ai.vector_store import get_vector_store, sync_jobs_to_vector_store, sync_companies_to_vector_store
from app.schemas.ai import (
    AIQueryRequest,
    JobRecommendationRequest,
    JobRecommendationResponse,
    JobDescriptionImprovementRequest,
    JobDescriptionImprovementResponse
)

router = APIRouter(
    prefix="/ai",
    tags=["AI Intelligence Layer"]
)

@router.post("/sync-vectors", status_code=status.HTTP_200_OK)
def sync_vectors(session: Session = Depends(get_session)):
    """
    Manually triggers the sync between PostgreSQL and ChromaDB.
    Call this after you add new jobs to update the AI's knowledge.
    """
    try:
        sync_jobs_to_vector_store(session)
        sync_companies_to_vector_store(session)
        return {"message": "Vectors synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
