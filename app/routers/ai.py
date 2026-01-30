from ast import Raise
from tabnanny import verbose
from fastapi import APIRouter, Depends, HTTPException, params, status
from sqlalchemy.engine import url
from sqlmodel import Session
import requests
import operator
import json
from typing import Optional,Annotated,TypedDict,Union,List
from app.ai import vector_store
from langchain_core.prompts import PromptTemplate  
from langchain_core.prompts import ChatPromptTemplate 
from langchain_core.tools import Tool,StructuredTool
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.database.session import get_session
from app.ai.llm import get_llm
from app.ai.vector_store import get_vector_store, sync_jobs_to_vector_store, sync_companies_to_vector_store,sync_applications_to_vector_store,sync_users_to_vector_store
from app.schemas.ai import (
    AIQueryRequest,
    JobRecommendationRequest,
    JobRecommendationResponse,
    JobDescriptionImprovementRequest,
    JobDescriptionImprovementResponse,
    ToolInput
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
        sync_applications_to_vector_store(session)
        sync_users_to_vector_store(session)
        return {"message": "Vectors synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/ask-ai")
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
    
    Question: {query}
    
    Answer:
    """

    
        QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

        qa_chain = QA_CHAIN_PROMPT | retriever | llm

    
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

API_BASE_URL = "http://127.0.0.1:8000"
@router.post("/agent")
def run_agent(request: AIQueryRequest):
    """
    An API-Driven Autonomous Agent.
    Includes Recruiter workflows, Loop Protection, and Defensive Argument Handling.
    """
    llm = get_llm(temperature=0)
    vector_store = get_vector_store()

    # --- TOOLS ---
    
    def vector_search_tool(query: str = ""):
        # Defensive check
        if not query: return "No query Provided"
        print(f"\n[AGENT ACTION] Searching Vector DB for: '{query}'")
        try:
            docs = vector_store.similarity_search(query, k=1)
            return "\n".join([f"Job Content: {d.page_content[:400]}" for d in docs])
        except Exception as e:
            return f"Search Error: {str(e)}"

    def fetch_jobs_api_tool(query: str = ""):
        try:
            # Defensive check
            if not query: query = ""
            
            print(f"\n[AGENT ACTION] Calling GET /jobs API with query: '{query}'")
            url = f"{API_BASE_URL}/jobs"
            
            query_params = {} 
            
            if query.strip():
                if query.startswith("{"):
                    try:
                        filters = json.loads(query)
                        for k, v in filters.items():
                            query_params[k] = str(v)
                    except:
                        query_params["q"] = query
                else:
                    query_params["q"] = query

            response = requests.get(url, params=query_params)
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("results", [])
                if not jobs: return "API returned 0 jobs."
                
                result = "\n".join([f"ID: {j['id']} | Title: {j['title']} | Loc: {j['location']}" for j in jobs])
                if len(result) > 3000: return result[:3000] + "...(truncated)"
                return result
            else:
                return f"API Error: {response.status_code}"
        except Exception as e:
            return f"Tool Execution Failed: {str(e)}"

    def fetch_applications_api_tool(query: str = ""):
        """
        Fetches candidates for a specific Job ID using the existing API.
        Input 'query' must be a numeric Job ID.
        """
        try:
            if not query or not query.strip().isdigit():
                return "Error: You must provide a numeric Job ID First find the job, then use its ID."
            
            job_id = query.strip()
            # Uses the endpoint: GET /jobs/{job_id}/applications
            url = f"{API_BASE_URL}/jobs/{job_id}/applications"
            
            print(f"\n[AGENT ACTION] Calling GET {url}")
            
            response = requests.get(url) 
            
            if response.status_code == 200:
                apps = response.json()
                if not apps: return f"No applications found for Job ID {job_id}."
                
                # Format candidate report with Skills
                report = []
                for app in apps:
                    seeker_id = app.get("job_seeker_id", "Unknown")
                    status = app.get("status", "Applied")
                    resume = app.get("resume_url", "No Resume")
                    
                    skills_list = app.get("skills", [])
                    if isinstance(skills_list, list):
                        skills_str = ", ".join(skills_list)
                    else:
                        skills_str = str(skills_list)

                    report.append(f"- Applicant ID: {seeker_id} | Status: {status} | Skills: {skills_str} | Resume: {resume}")
                
                return "\n".join(report)
            elif response.status_code == 403:
                 return "Error: 403 Forbidden. The Agent needs Recruiter permissions to view applications."
            else:
                return f"API Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error fetching applications: {str(e)}"

    def fetch_companies_api_tool(query: str = ""):
        # Accepts 'query' but ignores it to satisfy the universal schema
        try:
            print(f"\n[AGENT ACTION] Calling GET /companies API")
            response = requests.get(f"{API_BASE_URL}/companies")
            if response.status_code == 200:
                companies = response.json()
                return "\n".join([f"ID: {c['id']} | Name: {c['name']}" for c in companies])
            return "Failed to fetch companies."
        except Exception as e:
            return f"Error: {str(e)}"

    def check_duplicates_tool(query: str = ""):
        # Accepts 'query' but ignores it
        try:
            print(f"\n[AGENT ACTION] Running Duplicate Analysis Script...")
            response = requests.get(f"{API_BASE_URL}/jobs")
            if response.status_code != 200: return "Failed to fetch jobs."
            
            jobs = response.json().get("results", [])
            seen = {}
            duplicates = []
            
            for job in jobs:
                title = (job.get('title') or "").strip().lower()
                location = (job.get('location') or "").strip().lower()
                key = (title, location)
                
                if key in seen:
                    duplicates.append(f"- Job ID {job['id']} is a duplicate of {seen[key]}")
                else:
                    seen[key] = job['id']
            
            if not duplicates: return "Analysis Complete: No duplicates found."
            
            report = "DUPLICATES FOUND:\n" + "\n".join(duplicates[:10])
            if len(duplicates) > 10: report += f"\n...and {len(duplicates)-10} more."
            return report
        except Exception as e:
            return f"Analysis Failed: {str(e)}"

    def fetch_user_api_tool(query: str = ""):
        try:
            if not query or not query.strip().isdigit():
                return "Error: You must provide a numeric Job ID First find the job, then use its ID."
            
            user_id = query.strip()
            url = f"{API_BASE_URL}/users/{user_id}"
            
            print(f"\n[AGENT ACTION] Calling GET {url}")
            
            response = requests.get(url) 
            
            if response.status_code == 200:
                apps = response.json()
                if not apps: return f"No Users found for User ID {user_id}."
                
                # Format candidate report with Sk
                user_id = apps.get("id","Unknown")
                email = apps.get("email", "Unknown")
                    
                    
                return f"- Applicant ID: {user_id} |  Email: {email}"
                
                
            else:
                return f"API Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error fetching users: {str(e)}"


    def notify_admin_action(query: str = ""):
        # Defensive check
        if not query: query = "No message provided."
        print(f"\n[AGENT ACTION] Notifying Admin: '{query}'")
        return f"✅ SUCCESS: Admin notified."

    # --- REGISTER TOOLS ---
    # All tools now use the same safe 'ToolInput' schema
    tools = [
        StructuredTool.from_function(
            name="Vector_Search", 
            func=vector_search_tool, 
            description="Search jobs by meaning.",
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="Fetch_Jobs_API", 
            func=fetch_jobs_api_tool, 
            description="Get structured job data. Input is a search string.",
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="List_Companies_API", 
            func=fetch_companies_api_tool, 
            description="Get list of companies.",
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="Check_Duplicates", 
            func=check_duplicates_tool, 
            description="Check for duplicates.",
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="Notify_Admin", 
            func=notify_admin_action, 
            description="Send alert to admin.",
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="Fetch_Applications", 
            func=fetch_applications_api_tool, 
            description="Fetch candidates/applications for a numeric Job ID.", 
            args_schema=ToolInput
        ),
        StructuredTool.from_function(
            name="Fetch_Users", 
            func=fetch_user_api_tool, 
            description="Fetch User From User Id",
            args_schema=ToolInput
        )
    ]

    # --- PROMPT ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """You are an API-Driven Job Board Assistant.
         You do not have database access. You must use the provided API Tools.
         
         STRATEGY:
         1. **General Search:** Use 'Vector_Search' for topic/skill queries.
         2. **Job Lists:** Use 'Fetch_Jobs_API' for listing jobs. Input must be a simple string like 'Python' or 'Remote'.
         3. **Admin Tasks:** Use 'Check_Duplicates' to scan for issues and 'Notify_Admin' if found.
         
         RECRUITER REPORTS (New Capability):
         If asked for a candidate or applicant report:
         1. **Step 1:** Find the 'Job ID' using 'Fetch_Jobs_API'.
         2. **Step 2:** Use 'Fetch_Applications' with that numeric Job ID and Find 'Applicant ID or Seeker ID'.
         3. **Step 3:** Use 'Fetch Users' with that numeric 'Applicant ID or Seeker ID'
         4. **Step 4:** Summarize the candidates found, **specifically highlighting their skills match** for the role.
         STRICT OPERATIONAL RULES:
        1. **NO REPETITION:** If you call a tool and get a result, do NOT call that same tool again with the same query. Use the information you already have.
         2. **RECRUITER WORKFLOW:** To generate a candidate report, you ONLY need to:
            - Search once for the Job ID.
            - Fetch applications once using that ID.
            - Fetch user info once using the applicant ID.
         3. **FINISH FAST:** As soon as you have the candidate data, generate the final report. Do not perform any extra searches.
         4. **ERROR HANDLING:** If a tool returns a warning about 'requested results > elements', ignore the warning and treat the returned data as the full result set.

         RECRUITER REPORT WORKFLOW:
         If asked for applicants or candidates for a role:
         1. Call 'Fetch_Jobs_API' with the role name (e.g., 'Python').
         2. Look at the result and find the numeric 'Job ID'.
         3. Call 'Fetch_Applications' using ONLY that numeric ID.
         4. Look at the result and find the 'Applicant ID or Seeker ID'.
         5. Call 'Fetch_Users' using that numeric 'Applicant ID or Seeker ID'.
         6. STOP and generate the report.
         
         GUARDRAILS:
         - **NEVER** call the same tool twice with the same input.
         - If 'Vector_Search' doesn't give you a numeric Job ID, switch to 'Fetch_Jobs_API'.
         - Do not summarize until you have the candidate list.
         - If you hit a 500 error from a tool, tell the user the system is busy.
         RECRUITER WORKFLOW:
         1. Search for the job to find its unique numeric ID.
         2. **CRITICAL:** Use the exact ID returned by the tool. Do NOT invent or guess an ID.
         3. Call 'Fetch_Applications' using the ID you just found.
     
         STRICT RULES:
          - If the tool returns 'ID: 1', your next call MUST use '1'. 
         - Never use placeholder IDs like '5' or '123' unless they were explicitly returned by a previous tool call.
         - If no ID is found, stop and tell the user.
        
         CRITICAL RULES:
         - **SEQUENCE:** You MUST run 'Check_Duplicates' *before* calling 'Notify_Admin'. Never notify without checking first.
         - **ONE-SHOT ONLY:** Notify the admin exactly ONCE. After you send the alert, STOP immediately. Do not repeat the action.
         - **NO HALLUCINATION:** If 'Check_Duplicates' returns "No duplicates found", strictly reply "System is clean" and do NOT notify the admin.
         - **INPUTS:** 'Fetch_Applications' only accepts a numeric ID (e.g. "5"). Do not send text like "Job ID 5".
         - Do not invent tool arguments (like 'days', 'limit'). Use only the 'query' string.
         - If user asks for "Top 3", fetch jobs and then manually pick the top 3 in your final answer.
         - If no jobs match, say "No jobs found".
         - **NO REPETITION:** If a tool returns a result, do not call that same tool again with the same parameters. 
         - **INDEX WARNINGS:** If you see a warning about "requested results greater than elements in index", it simply means the database is small. Use the results you got anyway.
         - **FINAL ANSWER:** Once you have search results, provide your final answer immediately. Do not keep searching.
         """),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        return_intermediate_steps=True,
        max_execution_time=25,
        max_iterations=3,     
        handle_parsing_errors=True,
    )
    
    try:
        result = agent_executor.invoke({"input": request.query})
        
        return {
            "response": result["output"]
        }
    except Exception as e:
        print(f"Agent Crash: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
