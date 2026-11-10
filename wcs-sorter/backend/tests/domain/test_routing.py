"""
Testes de domínio — executam sem banco e sem container.
Cobre RF-02, RF-03, RF-04, RF-06, RF-07, RF-08, RN-03..RN-06, CA-02, CA-03, CA-06.
"""

from __future__ import annotations

import pytest

from app.domain.entities import Criterio, Mapa, Pedido, habilitar_mapa
from app.domain.errors import (
    ConflitoDestinosError,
    CriterioInvalidoError,
    MapeamentoDuplicadoError,
    MapaInvalidoError,
    SemRotaError,
)
from app.domain.routing import decidir_rota
from app.infrastructure.memory_repository import MemoryPedidoRepository


def _pedido(
    codigo: str,
    *,
    sigla: str | None = None,
    uf: str | None = None,
    filial: str | None = None,
    etiquetas: list[str] | None = None,
) -> Pedido:
    return Pedido(
        codigo_principal=codigo,
        sigla=sigla,
        uf=uf,
        filial=filial,
        etiquetas=etiquetas or [],
    )


def _mapa_sigla(*pares: tuple[str, int], habilitado: bool = True) -> Mapa:
    m = Mapa(criterio="sigla", habilitado=habilitado)
    for valor, saida in pares:
        m.adicionar_mapeamento(valor, saida)
    return m


def test_codigo_valido_com_rota_retorna_saida():
    """RF-02, CA-02 — um código válido com rota mapeada retorna código + saída."""
    pedidos = [_pedido("TRK001", sigla="SAO")]
    mapa = _mapa_sigla(("SAO", 3))
    decisao = decidir_rota(["XXX", "TRK001", "YYY"], pedidos, mapa)
    assert decisao.codigo == "TRK001"
    assert decisao.saida == 3


def test_codigos_com_destinos_conflitantes_rejeitam_consulta():
    """RF-03, RN-03, CA-03 — destinos distintos rejeitam e não devolvem saída."""
    pedidos = [
        _pedido("TRK001", sigla="SAO"),
        _pedido("TRK002", sigla="CWB"),
    ]
    mapa = _mapa_sigla(("SAO", 1), ("CWB", 2))
    with pytest.raises(ConflitoDestinosError):
        decidir_rota(["TRK001", "TRK002"], pedidos, mapa)


def test_nenhum_codigo_com_rota_indica_excecao():
    """RF-04 — nenhum código conhecido → SemRotaError."""
    pedidos = [_pedido("TRK001", sigla="SAO")]
    mapa = _mapa_sigla(("SAO", 1))
    with pytest.raises(SemRotaError):
        decidir_rota(["DESCONHECIDO1", "DESCONHECIDO2"], pedidos, mapa)


def test_alteracao_de_mapa_vale_na_consulta_seguinte():
    """RF-08, CA-06 — remapeamento no mesmo objeto vale na consulta seguinte."""
    pedidos = [_pedido("TRK001", sigla="SAO")]
    mapa = _mapa_sigla(("SAO", 1))
    d1 = decidir_rota(["TRK001"], pedidos, mapa)
    assert d1.saida == 1

    mapa.remapear("SAO", 7)
    d2 = decidir_rota(["TRK001"], pedidos, mapa)
    assert d2.saida == 7


def test_adicionar_mapeamento_rejeita_duplicidade_divergente():
    """RN-06 — adicionar_mapeamento continua rejeitando o mesmo valor em outra saída."""
    mapa = Mapa(criterio="sigla", habilitado=True)
    mapa.adicionar_mapeamento("SAO", 1)
    with pytest.raises(MapeamentoDuplicadoError):
        mapa.adicionar_mapeamento("SAO", 7)


def test_mesmo_valor_nao_mapeia_duas_saidas():
    """RN-06, RNF-05 — mesmo valor em duas saídas é rejeitado."""
    mapa = Mapa(criterio="sigla", habilitado=True)
    mapa.adicionar_mapeamento("SAO", 1)
    with pytest.raises(MapeamentoDuplicadoError):
        mapa.adicionar_mapeamento("sao", 2)  # case-insensitive


def test_apenas_um_mapa_habilitado():
    """RF-06, RN-04 — habilitar_mapa deixa exatamente um ONLINE."""
    m1 = _mapa_sigla(("SAO", 1), habilitado=True)
    m2 = _mapa_sigla(("CWB", 2), habilitado=False)
    habilitar_mapa([m1, m2], m2)
    assert m2.habilitado is True
    assert m1.habilitado is False

    with pytest.raises(MapaInvalidoError):
        decidir_rota(["TRK001"], [_pedido("TRK001", sigla="SAO")], m1)


def test_criterio_so_aceita_sigla_uf_ou_filial():
    """RF-07, RN-05 — critério inválido é rejeitado."""
    with pytest.raises(CriterioInvalidoError):
        Criterio("cep")
    assert Criterio("sigla").valor == "sigla"
    assert Criterio("UF").valor == "uf"
    assert Criterio("Filial").valor == "filial"


def test_mapa_por_uf_roteia_pelo_campo_uf():
    """RF-07 — mapa por UF usa o campo uf do pedido."""
    pedidos = [_pedido("TRK001", sigla="SAO", uf="SP")]
    mapa = Mapa(criterio="uf", habilitado=True)
    mapa.adicionar_mapeamento("SP", 5)
    decisao = decidir_rota(["TRK001"], pedidos, mapa)
    assert decisao.saida == 5
    assert decisao.codigo == "TRK001"


def test_repositorio_em_memoria_busca_por_codigos():
    """Porta PedidoRepository — adaptador em memória."""
    repo = MemoryPedidoRepository(
        [
            _pedido("TRK001", sigla="SAO", etiquetas=["E1"]),
            _pedido("TRK002", sigla="CWB"),
        ]
    )
    achados = repo.buscar_por_codigos(["E1", "XXX"])
    assert len(achados) == 1
    assert achados[0].codigo_principal == "TRK001"
