from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import GROQ_API_KEY,EMBEDDING_MODEL_NAME

def get_llm(temperature=0.0):
    """
    Returns the ChatGroq instance.
    
    Args:
        temperature (float): Controls randomness. 
                             0.0 = Fact-based (good for RAG).
                             0.7 = Creative (good for writing descriptions).
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing in environment variables.")

    return ChatGroq(
        api_key=GROQ_API_KEY, 
        model_name="llama-3.1-8b-instant",
        temperature=temperature
    )

def get_embeddings():
    """
    Returns the embedding model used to convert text into vectors.
    Using HuggingFace (runs locally on CPU).
    """
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


