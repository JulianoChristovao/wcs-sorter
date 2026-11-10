"""
Serviço de lógica de negócio do Sorter.

Regra de negócio:
- O sorter lê TODOS os códigos de barras da caixa (desconhecidos a priori).
- Envia a lista separada por ';' ao WCS.
- O WCS identifica qual código corresponde a uma etiqueta de rastreio
  de pedido pendente e retorna esse código + a saída mapeada.
- Se MAIS DE UM código corresponder a pedidos pendentes com destino,
  retorna ERRO (múltiplos destinos).

A decisão de roteamento é delegada ao domínio (app.domain.decidir_rota).
"""
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Mapa as MapaDominio, Pedido as PedidoDominio
from app.domain.errors import DomainError
from app.domain.routing import decidir_rota
from app.models.pedido import Pedido, PedidoEtiqueta, ConfirmacaoSorter, PedidoStatus
from app.models.rota import MapeamentoRotaSaida, Saida, Mapa
from app.models.log import LogSorter
from app.schemas.sorter import (
    ConsultaEtiquetaRequest,
    ConsultaEtiquetaResponse,
    ConfirmacaoSorterRequest,
    ConfirmacaoSorterResponse,
)


class SorterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def consultar_etiqueta(
        self, payload: ConsultaEtiquetaRequest
    ) -> ConsultaEtiquetaResponse:
        """
        Recebe todos os códigos lidos na caixa (separados por ';').
        Identifica a etiqueta de rastreio válida e retorna código + saída.
        """
        inicio = time.perf_counter()
        codigos = [c.strip() for c in payload.etiqueta.split(";") if c.strip()]

        if not codigos:
            await self._log_sorter(
                tipo="consulta",
                payload_entrada=payload.model_dump(),
                sucesso=False,
                mensagem="Nenhum código válido na leitura",
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError("Nenhum código de barras válido informado")

        status_pendentes = [
            PedidoStatus.recebido,
            PedidoStatus.pendente,
            PedidoStatus.em_processamento,
        ]

        # Persistência: pedidos candidatos (adaptador → entidades de domínio)
        stmt = (
            select(Pedido)
            .outerjoin(PedidoEtiqueta, PedidoEtiqueta.pedido_id == Pedido.id)
            .where(
                and_(
                    Pedido.status.in_(status_pendentes),
                    (
                        Pedido.codigo_principal.in_(codigos)
                        | PedidoEtiqueta.codigo.in_(codigos)
                    ),
                )
            )
            .options(selectinload(Pedido.etiquetas))
            .distinct()
        )
        result = await self.db.execute(stmt)
        pedidos_orm = list(result.scalars().all())

        mapa_dominio = await self._carregar_mapa_dominio()
        pedidos_dominio = [self._pedido_para_dominio(p) for p in pedidos_orm]

        try:
            decisao = decidir_rota(codigos, pedidos_dominio, mapa_dominio)
        except DomainError as exc:
            await self._log_sorter(
                tipo="consulta",
                payload_entrada=payload.model_dump(),
                sucesso=False,
                mensagem=str(exc),
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError(str(exc)) from exc

        # Localiza o ORM correspondente para atualizar status
        pedido = next(
            (p for p in pedidos_orm if p.codigo_principal == decisao.codigo),
            None,
        )
        if pedido is None:
            # fallback: match por etiqueta associada
            for p in pedidos_orm:
                etqs = {p.codigo_principal}
                etqs.update(e.codigo for e in (p.etiquetas or []))
                if decisao.codigo in etqs:
                    pedido = p
                    break
        if pedido is None:
            raise ValueError("Pedido da decisão não encontrado na base")

        pedido.status = PedidoStatus.em_processamento
        pedido.processado_em = datetime.now(timezone.utc)

        response = ConsultaEtiquetaResponse(
            codigo=decisao.codigo, saida=decisao.saida
        )

        await self._log_sorter(
            tipo="consulta",
            payload_entrada=payload.model_dump(),
            payload_saida=response.model_dump(),
            codigo_encontrado=decisao.codigo,
            saida_retornada=decisao.saida,
            sucesso=True,
            tempo_ms=int((time.perf_counter() - inicio) * 1000),
        )

        return response

    async def confirmar_separacao(
        self, payload: ConfirmacaoSorterRequest
    ) -> ConfirmacaoSorterResponse:
        """Confirma separação com dados aferidos e notifica o WMS."""
        inicio = time.perf_counter()

        stmt = (
            select(Pedido)
            .where(
                and_(
                    Pedido.codigo_principal == payload.codigo,
                    Pedido.status.in_(
                        [
                            PedidoStatus.em_processamento,
                            PedidoStatus.pendente,
                            PedidoStatus.recebido,
                        ]
                    ),
                )
            )
        )
        result = await self.db.execute(stmt)
        pedido = result.scalar_one_or_none()

        if not pedido:
            await self._log_sorter(
                tipo="confirmacao",
                payload_entrada=payload.model_dump(mode="json"),
                sucesso=False,
                mensagem="Pedido não encontrado ou já processado",
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError("Pedido não encontrado ou já processado")

        confirmacao = ConfirmacaoSorter(
            pedido_id=pedido.id,
            codigo=payload.codigo,
            altura_cm=payload.altura,
            largura_cm=payload.largura,
            comprimento_cm=payload.comprimento,
            peso_kg=payload.peso,
            saida_numero=payload.saida,
            dados_brutos=payload.model_dump(mode="json"),
        )
        self.db.add(confirmacao)

        pedido.status = PedidoStatus.separado
        pedido.confirmado_em = datetime.now(timezone.utc)

        await self.db.flush()

        from app.services.wms_service import WmsService

        wms_service = WmsService(self.db)
        await wms_service.notificar_separacao_concluida(pedido, confirmacao)

        response = ConfirmacaoSorterResponse(
            sucesso=True,
            mensagem="Separação confirmada com sucesso",
            pedido_id=str(pedido.id),
        )

        await self._log_sorter(
            tipo="confirmacao",
            payload_entrada=payload.model_dump(mode="json"),
            payload_saida=response.model_dump(),
            codigo_encontrado=payload.codigo,
            saida_retornada=payload.saida,
            sucesso=True,
            tempo_ms=int((time.perf_counter() - inicio) * 1000),
        )

        return response

    def _pedido_para_dominio(self, pedido: Pedido) -> PedidoDominio:
        etiquetas = [e.codigo for e in (pedido.etiquetas or []) if e.codigo]
        return PedidoDominio(
            codigo_principal=pedido.codigo_principal,
            sigla=pedido.sigla,
            uf=pedido.uf,
            filial=pedido.filial,
            etiquetas=etiquetas,
            rota_codigo=pedido.rota_codigo,
        )

    async def _carregar_mapa_dominio(self) -> Optional[MapaDominio]:
        result = await self.db.execute(
            select(Mapa)
            .where(Mapa.habilitado.is_(True))
            .options(selectinload(Mapa.mapeamentos).selectinload(MapeamentoRotaSaida.saida))
        )
        mapa_orm = result.scalar_one_or_none()
        if not mapa_orm:
            return None

        criterio = (
            mapa_orm.criterio_roteamento.value
            if hasattr(mapa_orm.criterio_roteamento, "value")
            else str(mapa_orm.criterio_roteamento)
        )
        mapa = MapaDominio(
            criterio=criterio,
            habilitado=True,
            nome=mapa_orm.nome or "",
        )
        for m in mapa_orm.mapeamentos or []:
            if not m.ativo:
                continue
            saida_num = m.saida.numero if m.saida is not None else None
            if saida_num is None:
                continue
            try:
                mapa.adicionar_mapeamento(m.valor, saida_num)
            except DomainError:
                # mapeamento inconsistente no banco: ignora duplicata divergente
                continue
        return mapa

    async def _log_sorter(
        self,
        tipo: str,
        payload_entrada: Optional[dict] = None,
        payload_saida: Optional[dict] = None,
        codigo_encontrado: Optional[str] = None,
        saida_retornada: Optional[int] = None,
        tempo_ms: Optional[int] = None,
        sucesso: bool = True,
        mensagem: Optional[str] = None,
    ) -> None:
        log = LogSorter(
            tipo=tipo,
            payload_entrada=payload_entrada,
            payload_saida=payload_saida,
            codigo_encontrado=codigo_encontrado,
            saida_retornada=saida_retornada,
            tempo_ms=tempo_ms,
            sucesso=sucesso,
            mensagem=mensagem,
        )
        self.db.add(log)
        await self.db.flush()
        # Em falha a API sobe HTTPException e o get_db faz rollback.
        # Commit imediato garante que o log de erro permaneça para o dashboard.
        if not sucesso:
            await self.db.commit()
