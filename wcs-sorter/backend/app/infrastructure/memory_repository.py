"""Adaptador em memória da porta PedidoRepository (testes de domínio)."""

from __future__ import annotations

from typing import List, Sequence

from app.domain.entities import Pedido


class MemoryPedidoRepository:
    """Implementação in-memory de PedidoRepository para testes sem banco."""

    def __init__(self, pedidos: Sequence[Pedido] | None = None):
        self._pedidos: List[Pedido] = list(pedidos or [])

    def add(self, pedido: Pedido) -> None:
        self._pedidos.append(pedido)

    def buscar_por_codigos(self, codigos: Sequence[str]) -> List[Pedido]:
        conjunto = {c.strip().casefold() for c in codigos if c and str(c).strip()}
        if not conjunto:
            return []
        encontrados: List[Pedido] = []
        for p in self._pedidos:
            ids = {c.casefold() for c in p.codigos_identificadores()}
            if ids & conjunto:
                encontrados.append(p)
        return encontrados
