"""
Schemas de autenticação.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    nome_completo: str
    role: str
    ativo: bool
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}