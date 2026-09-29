from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class LogsPage(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: list[T]


class LogSorterResponse(BaseModel):
    id: str
    tipo: str
    codigo_encontrado: Optional[str] = None
    saida_retornada: Optional[int] = None
    tempo_ms: Optional[int] = None
    sucesso: bool
    mensagem: Optional[str] = None
    payload_entrada: Optional[dict[str, Any]] = None
    payload_saida: Optional[dict[str, Any]] = None
    created_at: datetime


class LogWmsResponse(BaseModel):
    id: str
    pedido_id: Optional[str] = None
    tipo: str
    sucesso: Optional[bool] = None
    mensagem_erro: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    resposta: Optional[dict[str, Any]] = None
    created_at: datetime
