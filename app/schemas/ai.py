from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional,List

class AIQueryRequest(BaseModel):
    query: str = Field(..., description="The query to search for in the job board.")

class JobRecommendationRequest(BaseModel):
    resume_text: str = Field(..., description="The resume text to use for job recommendation.")

class JobRecommendationResponse(BaseModel):
    resume_text: str = Field(..., description="The resume text to use for job recommendation.")

class ImprovementMode(str,Enum):
    short="short"
    detailed="detailed"
    marketing="marketing"

class JobDescriptionImprovementResponse(BaseModel):
    original_description: str = Field(..., description="The original job description.")
    improved_description: str = Field(..., description="The improved job description.")
    improvement_mode: str = Field(..., description="The improvement mode.")

class JobDescriptionImprovementRequest(BaseModel):
    title: str = Field(..., description="The title of the job.")
    description: str = Field(..., description="The description of the job.")
    mode: ImprovementMode = Field(..., description="The improvement mode.")

    