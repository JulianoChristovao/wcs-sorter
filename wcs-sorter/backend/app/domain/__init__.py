"""Pacote de domínio WCS — sem dependência de ORM, FastAPI ou Pydantic."""

from app.domain.entities import Criterio, Decisao, Mapa, Pedido, habilitar_mapa
from app.domain.errors import (
    ConflitoDestinosError,
    CriterioInvalidoError,
    DomainError,
    MapeamentoDuplicadoError,
    MapaInvalidoError,
    SemRotaError,
)
from app.domain.ports import PedidoRepository
from app.domain.routing import consultar, decidir_rota

__all__ = [
    "Criterio",
    "Decisao",
    "Mapa",
    "Pedido",
    "PedidoRepository",
    "habilitar_mapa",
    "consultar",
    "decidir_rota",
    "DomainError",
    "ConflitoDestinosError",
    "CriterioInvalidoError",
    "MapeamentoDuplicadoError",
    "MapaInvalidoError",
    "SemRotaError",
]

