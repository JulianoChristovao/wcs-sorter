"""
Schemas das APIs do Sorter (machine-to-machine).
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ConsultaEtiquetaRequest(BaseModel):
    """Payload enviado pelo sorter ao ler os códigos de barras da caixa."""
    etiqueta: str = Field(
        ...,
        description="Códigos de barras separados por ponto-e-vírgula (;)",
        examples=["ABC1234;FFFF45678;123456789"],
    )


class ConsultaEtiquetaResponse(BaseModel):
    """Resposta do WCS indicando o código correto e a rampa de destino."""
    codigo: str = Field(..., description="Código principal identificado")
    saida: int = Field(..., description="Número da saída/rampa do sorter", ge=1)


class ConfirmacaoSorterRequest(BaseModel):
    """Confirmação de separação enviada pelo sorter com dados aferidos."""
    codigo: str = Field(..., min_length=1, max_length=100)
    altura: Optional[Decimal] = Field(None, ge=0, description="Altura em cm")
    largura: Optional[Decimal] = Field(None, ge=0, description="Largura em cm")
    comprimento: Optional[Decimal] = Field(None, ge=0, description="Comprimento em cm")
    peso: Optional[Decimal] = Field(None, ge=0, description="Peso em kg")
    saida: int = Field(..., ge=1, description="Saída utilizada")


class ConfirmacaoSorterResponse(BaseModel):
    sucesso: bool
    mensagem: str
    pedido_id: Optional[str] = None