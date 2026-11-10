"""Portas (interfaces) declaradas pelo domínio."""

from __future__ import annotations

from typing import List, Protocol, Sequence

from app.domain.entities import Pedido


class PedidoRepository(Protocol):
    """O domínio pede pedidos pendentes cujos códigos estejam no conjunto lido."""

    def buscar_por_codigos(self, codigos: Sequence[str]) -> List[Pedido]:
        ...
