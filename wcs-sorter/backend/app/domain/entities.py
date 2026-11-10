"""Entidades e objetos de valor do domínio WCS (sem ORM/HTTP)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from app.domain.errors import (
    CriterioInvalidoError,
    MapeamentoDuplicadoError,
    MapaInvalidoError,
)


class Criterio:
    """Objeto de valor: um mapa só usa sigla, uf ou filial (RN-05)."""

    PERMITIDOS = frozenset({"sigla", "uf", "filial"})

    def __init__(self, valor: str):
        normalizado = (valor or "").strip().lower()
        if normalizado not in self.PERMITIDOS:
            raise CriterioInvalidoError(
                f"Critério inválido: '{valor}'. Use sigla, uf ou filial."
            )
        self._valor = normalizado

    @property
    def valor(self) -> str:
        return self._valor

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Criterio):
            return NotImplemented
        return self._valor == other._valor

    def __hash__(self) -> int:
        return hash(self._valor)

    def __str__(self) -> str:
        return self._valor

    def __repr__(self) -> str:
        return f"Criterio({self._valor!r})"


@dataclass
class Pedido:
    """Volume esperado pelo WCS; identifica-se por códigos e expõe destino por critério."""

    codigo_principal: str
    sigla: Optional[str] = None
    uf: Optional[str] = None
    filial: Optional[str] = None
    etiquetas: List[str] = field(default_factory=list)
    rota_codigo: Optional[str] = None  # legado/display; fallback de sigla

    def codigos_identificadores(self) -> set[str]:
        codes = {self.codigo_principal}
        codes.update(e for e in self.etiquetas if e)
        return {c.strip() for c in codes if c and c.strip()}

    def valor_destino(self, criterio: Criterio) -> Optional[str]:
        if criterio.valor == "sigla":
            raw = self.sigla or self.rota_codigo
        elif criterio.valor == "uf":
            raw = self.uf
        else:
            raw = self.filial
        if raw is None:
            return None
        valor = str(raw).strip()
        return valor if valor else None


@dataclass(frozen=True)
class Decisao:
    """Resultado imutável da consulta de roteamento."""

    codigo: str
    saida: int


class Mapa:
    """
    Associação valor → saída de um critério.
    Protege RN-06 (mesmo valor não vai a duas saídas) e RN-04 (habilitação).
    """

    def __init__(
        self,
        criterio: Criterio | str,
        mapeamentos: Optional[Dict[str, int]] = None,
        habilitado: bool = False,
        nome: str = "",
    ):
        if isinstance(criterio, str):
            criterio = Criterio(criterio)
        self.criterio = criterio
        self.habilitado = habilitado
        self.nome = nome
        # chave normalizada (casefold) → número da saída
        self._mapeamentos: Dict[str, int] = {}
        if mapeamentos:
            for valor, saida in mapeamentos.items():
                self.adicionar_mapeamento(valor, saida)

    def adicionar_mapeamento(self, valor: str, saida: int) -> None:
        chave = str(valor).strip().casefold()
        if not chave:
            raise MapaInvalidoError("Valor de mapeamento vazio")
        if chave in self._mapeamentos and self._mapeamentos[chave] != saida:
            raise MapeamentoDuplicadoError(
                f"Valor '{valor}' já mapeado para saída {self._mapeamentos[chave]}"
            )
        self._mapeamentos[chave] = int(saida)

    def remapear(self, valor: str, saida: int) -> None:
        """Troca a saída de um valor já mapeado (ou cria o mapeamento).

        Diferente de adicionar_mapeamento, não lança MapeamentoDuplicadoError
        quando o valor já existe com outra saída. Sustenta CA-06.
        """
        chave = str(valor).strip().casefold()
        if not chave:
            raise MapaInvalidoError("Valor de mapeamento vazio")
        self._mapeamentos[chave] = int(saida)

    def resolver_saida(self, valor: Optional[str]) -> Optional[int]:
        if valor is None:
            return None
        chave = str(valor).strip().casefold()
        return self._mapeamentos.get(chave)

    @property
    def mapeamentos(self) -> Dict[str, int]:
        return dict(self._mapeamentos)


def habilitar_mapa(mapas: Iterable[Mapa], escolhido: Mapa) -> None:
    """Garante exatamente um mapa ONLINE (RN-04) no conjunto em memória."""
    for m in mapas:
        m.habilitado = m is escolhido
    escolhido.habilitado = True
