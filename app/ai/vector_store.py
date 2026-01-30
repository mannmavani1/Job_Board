import os
import shutil
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sqlmodel import Session,select
from app.models.job import Job
from app.models.company import Company
from app.ai.llm import get_embeddings

PERSIST_DIR = "./chroma_db"

def get_vector_store():
    """
    Initialize the Chroma vector store with our embedding model.
    Data is saved to the 'chroma_db' folder locally.
    """
    return Chroma(
        collection_name="job_board_data",
        embedding_function=get_embeddings(),
        persist_directory=PERSIST_DIR
    )

def sync_jobs_to_vector_store(session: Session):
    """
    Reads ALL active jobs from PostgreSQL and upserts them into ChromaDB.
    
    How it works:
    1. Fetches all active jobs from SQL.
    2. Converts them into a text format the AI can understand.
    3. Wraps them in 'Document' objects with metadata (ID, Location).
    4. Saves them to ChromaDB.
    """
    vector_store = get_vector_store()

    jobs = session.exec(select(Job).where(Job.is_active == True)).all()

    if not jobs:
        print("No active jobs found in the database.")
        return
    documents = []
    print(f"Found {len(jobs)} active jobs to sync. Syncing to ChromaDB...")

    for job in jobs:

        page_content = (
            f"Job Title: {job.title}\n"
            f"Job Location: {job.location}\n"
            f"Job Type: {job.job_type}\n"
            f"Job Experience Level: {job.experience_level}\n"
            f"Job Salary Range: {job.salary_min} - {job.salary_max}\n"
           
            f"Job Description: {job.description}\n"
        )

        metadata = {
            "id": job.id,
            "company_id": job.company_id,
            "type": "job",
            "location": job.location or "Remote"
        }

        documents.append(Document(page_content=page_content, metadata=metadata))

        vector_store.add_documents(documents)

        print(f"Synced {len(jobs)} active jobs to ChromaDB.")

def sync_companies_to_vector_store(session: Session):
    vector_store = get_vector_store()

    companies = session.exec(select(Company)).all()

    if not companies:
        print("No companies found in the database.")
        return
    documents = []
    print(f"Found {len(companies)} companies to sync. Syncing to ChromaDB...")

    for company in companies:

        page_content = (
            f"Company Name: {company.name}\n"
            f"Company Description: {company.description}\n"
            f"Company Website: {company.website}\n"
            f"Company Location: {company.location}\n"
        )

        metadata = {
            "id": company.id,
            "type": "company",
            "location": company.location
        }

        documents.append(Document(page_content=page_content, metadata=metadata))

        vector_store.add_documents(documents)

        print(f"Synced {len(companies)} companies to ChromaDB.")
