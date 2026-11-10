"""Funções puras de roteamento (RN-02, RN-03, RN-04) — sem ORM/HTTP."""

from __future__ import annotations

from typing import Optional, Sequence

from app.domain.entities import Decisao, Mapa, Pedido
from app.domain.errors import ConflitoDestinosError, MapaInvalidoError, SemRotaError


def _normalizar_codigos(codigos: Sequence[str]) -> list[str]:
    return [c.strip() for c in codigos if c and str(c).strip()]


def decidir_rota(
    codigos: Sequence[str],
    pedidos: Sequence[Pedido],
    mapa: Optional[Mapa],
) -> Decisao:
    """
    Dados os códigos lidos, os pedidos candidatos e o mapa ONLINE,
    devolve a decisão (código + saída) ou levanta erro de negócio.
    """
    codigos_norm = _normalizar_codigos(codigos)
    if not codigos_norm:
        raise SemRotaError("Nenhum código de barras válido informado")

    if mapa is None or not mapa.habilitado:
        raise MapaInvalidoError("Nenhum mapa habilitado")

    # Pedidos que batem com algum código lido
    candidatos: list[Pedido] = []
    conjunto = {c.casefold() for c in codigos_norm}
    for p in pedidos:
        ids = {c.casefold() for c in p.codigos_identificadores()}
        if ids & conjunto:
            candidatos.append(p)

    if not candidatos:
        raise SemRotaError(
            "Nenhuma etiqueta de rastreio conhecida entre os códigos lidos"
        )

    # Destinos distintos segundo o critério do mapa → conflito
    destinos: dict[str, Pedido] = {}
    for p in candidatos:
        valor = p.valor_destino(mapa.criterio)
        chave = (valor or "").casefold()
        # sem valor de destino: trata como destino vazio distinto
        if chave not in destinos:
            destinos[chave] = p

    if len(destinos) > 1:
        etiquetas = [p.codigo_principal for p in candidatos]
        rotas = [p.valor_destino(mapa.criterio) for p in candidatos]
        raise ConflitoDestinosError(
            f"Múltiplos destinos encontrados nos códigos lidos: "
            f"etiquetas={etiquetas}, destinos={rotas}"
        )

    pedido = candidatos[0]
    valor = pedido.valor_destino(mapa.criterio)
    if not valor:
        raise SemRotaError(
            f"Pedido sem valor para critério '{mapa.criterio.valor}'"
        )

    saida = mapa.resolver_saida(valor)
    if saida is None:
        raise SemRotaError(
            f"Sem mapeamento para {mapa.criterio.valor}='{valor}' no mapa habilitado"
        )

    return Decisao(codigo=pedido.codigo_principal, saida=saida)


def consultar(
    codigos: Sequence[str],
    pedidos: Sequence[Pedido],
    mapa: Optional[Mapa],
) -> Decisao:
    """Alias estável para a decisão de roteamento (API do domínio)."""
    return decidir_rota(codigos, pedidos, mapa)
