from uuid import UUID
from pydantic import BaseModel, EmailStr, Field




class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(recruiter|job_seeker)$")


class UserRegisterResponse(BaseModel):
    id: int    
    email: EmailStr
    role: str
    is_active: bool



class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"




class TokenPayload(BaseModel):
    sub: str
    exp: int
