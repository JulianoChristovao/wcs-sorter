"""
Schemas de Mapas, Rotas, Saídas e Mapeamento.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


CriterioLiteral = Literal["sigla", "uf", "filial"]


class MapaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    quantidade_saidas: int = Field(default=8, ge=1, le=100)
    criterio_roteamento: CriterioLiteral = Field(
        default="sigla",
        description="Único critério deste mapa: sigla, uf ou filial",
    )
    habilitado: bool = False


class MapaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    quantidade_saidas: Optional[int] = Field(None, ge=1, le=100)
    criterio_roteamento: Optional[CriterioLiteral] = None


class MapaResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    quantidade_saidas: int
    criterio_roteamento: str
    habilitado: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RotaCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    descricao: str = Field(..., min_length=1, max_length=150)


class RotaResponse(BaseModel):
    id: int
    codigo: str
    descricao: str
    ativo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SaidaResponse(BaseModel):
    id: int
    numero: int
    descricao: Optional[str]
    ativo: bool

    model_config = {"from_attributes": True}


class MapeamentoCreate(BaseModel):
    mapa_id: int
    valor: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Valor conforme critério do mapa (ex: SAO, SP ou Braz)",
    )
    saida_numero: int = Field(..., ge=1)
    # legado
    rota_codigo: Optional[str] = None


class MapeamentoResponse(BaseModel):
    id: int
    mapa_id: int
    valor: str
    rota_codigo: Optional[str] = None
    rota_descricao: Optional[str] = None
    saida_numero: int
    saida_descricao: Optional[str]
    ativo: bool

    model_config = {"from_attributes": True}


class ConfigSorterUpdate(BaseModel):
    quantidade_saidas: int = Field(..., ge=1, le=100)
    descricao: Optional[str] = None


class ConfigSorterResponse(BaseModel):
    id: int
    quantidade_saidas: int
    descricao: Optional[str]
    ativo: bool
    updated_at: datetime

    model_config = {"from_attributes": True}
