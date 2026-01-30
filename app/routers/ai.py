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


@router.post("ask-ai")
def ask_ai(request: AIQueryRequest):
    try:
        llm = get_llm(temperature=0.0)
        vector_store = get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        template = """
    You are a helpful assistant for a Job Board. 
    Use the following pieces of context (Job Listings) to answer the user's question.
    If you don't know the answer, just say you don't know. Do not make up jobs.
    
    Context:
    {context}
    
    Question: {question}
    
    Answer:
    """

    
        QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

        qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=retriever,
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
    )

    
        result = qa_chain.invoke({"query": request.query})

        return {"answer": result["result"]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/recommend-jobs", status_code=status.HTTP_200_OK)
def recommend_jobs(request: JobRecommendationRequest):
    try:
        llm = get_llm(temperature=0.0)
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(request.resume_text, k=1)

        recommendations = []
        for doc in docs:
            job_id = doc.metadata.get("id")
            job_content = doc.page_content

            prompt = f"""
        Analyze the fit between a candidate and a job.
        
        Candidate Profile Summary: {request.resume_text[:1000]}...
        Job Details: {job_content}
        
        Explain briefly (1 sentence) why this candidate is a good match and give a match percentage.
        Format: "Reason | Percentage"
        """
            try:
                response = llm.invoke(prompt).content
                recommendations.append({
                    "job_id": job_id,
                    "job_content": job_content,
                    "ai_analysis": response
                })
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/improve-job-description", response_model=JobDescriptionImprovementResponse)
def improve_job_description(request: JobDescriptionImprovementRequest):
    try:
        llm = get_llm(temperature=0.7)


        base_instruction = (
        "You are an expert Technical Recruiter and Copywriter. "
        "Your goal is to rewrite the provided job description. "
        "Fix all grammar issues. "
        f"Ensure the content is optimized for SEO targeting the job title: '{request.title}'. "
        )
        if request.mode == "short":
            specific_instruction = (
            "STYLE: Short, crisp, and scannable.\n"
            "- Use bullet points heavily.\n"
            "- Remove generic corporate fluff.\n"
            "- Keep sentences under 15 words.\n"
            "- Focus on 'Must Haves' vs 'Nice to Haves'."
            )
        elif request.mode == "marketing":
            specific_instruction = (
            "STYLE: Engaging, exciting, and candidate-centric.\n"
            "- Use an energetic and welcoming tone.\n"
            "- Highlight growth opportunities and company culture.\n"
            "- Use persuasive language to attract top talent."
            )
        else:
            specific_instruction = (
            "STYLE: Professional, corporate, and comprehensive.\n"
            "- Use formal business English.\n"
            "- Structure with clear headers: 'About the Role', 'Key Responsibilities', 'Requirements'.\n"
            "- Ensure clarity on deliverables."
            )

        prompt = f"""
        {base_instruction}
        {specific_instruction}
    
         ---
        ORIGINAL DESCRIPTION:
        {request.description}
        ---
    
        OUTPUT (Return ONLY the improved description text):
        """

        response = llm.invoke(prompt)

        return {
        "original_description": request.description,
        "improved_description": response.content,
        "improvement_mode": request.mode
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) 