"""
Schemas de Pedidos.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PedidoCreate(BaseModel):
    """
    Payload flexível do WMS.

    Exemplo:
    {
      "codigo_externo": "NF-111111111111111",
      "etiqueta": "FFFF45678",
      "sigla": "SAO",
      "UF": "SP",
      "Filial": "Braz"
    }
    """
    codigo_externo: Optional[str] = None
    etiqueta: str = Field(..., min_length=1, max_length=100)
    sigla: Optional[str] = Field(None, max_length=50)
    uf: Optional[str] = Field(None, max_length=10, alias="UF")
    filial: Optional[str] = Field(None, max_length=100, alias="Filial")
    rota_codigo: Optional[str] = Field(None, max_length=100)
    prioridade: int = Field(default=5, ge=1, le=10)
    dados_extras: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def pelo_menos_um_destino(self):
        if not any([self.sigla, self.uf, self.filial, self.rota_codigo]):
            raise ValueError(
                "Informe ao menos um destino: sigla, UF, Filial ou rota_codigo"
            )
        return self


class PedidoResponse(BaseModel):
    id: UUID
    codigo_externo: Optional[str] = None
    etiqueta: str
    sigla: Optional[str] = None
    uf: Optional[str] = None
    filial: Optional[str] = None
    rota_codigo: str
    status: str
    created_at: datetime
    processado_em: Optional[datetime] = None
    confirmado_em: Optional[datetime] = None
    # Dados aferidos pelo sorter (última confirmação)
    altura_cm: Optional[float] = None
    largura_cm: Optional[float] = None
    comprimento_cm: Optional[float] = None
    peso_kg: Optional[float] = None
    saida_confirmada: Optional[int] = None

    model_config = {"from_attributes": True}


class PedidoListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[PedidoResponse]
