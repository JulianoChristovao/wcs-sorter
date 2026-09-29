"""
Schemas de Usuários.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    nome_completo: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(..., pattern=r"^(admin|gestor|operador)$")


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = Field(None, min_length=3, max_length=150)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    role: Optional[str] = Field(None, pattern=r"^(admin|gestor|operador)$")
    ativo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    id: UUID
    username: str
    email: str
    nome_completo: str
    role: str
    ativo: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}