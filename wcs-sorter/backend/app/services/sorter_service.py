"""
Serviço de lógica de negócio do Sorter.

Regra de negócio:
- O sorter lê TODOS os códigos de barras da caixa (desconhecidos a priori).
- Envia a lista separada por ';' ao WCS.
- O WCS identifica qual código corresponde a uma etiqueta de rastreio
  de pedido pendente e retorna esse código + a saída mapeada.
- Se MAIS DE UM código corresponder a pedidos pendentes com destino,
  retorna ERRO (múltiplos destinos).
"""
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pedido import Pedido, PedidoEtiqueta, ConfirmacaoSorter, PedidoStatus
from app.models.rota import MapeamentoRotaSaida, Rota, Saida
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

        # Busca pedidos pendentes cuja etiqueta de rastreio está entre os códigos lidos
        # (via tabela pedido_etiquetas OU codigo_principal)
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
        pedidos_encontrados = list(result.scalars().all())

        if not pedidos_encontrados:
            await self._log_sorter(
                tipo="consulta",
                payload_entrada=payload.model_dump(),
                sucesso=False,
                mensagem="Nenhuma etiqueta de rastreio conhecida entre os códigos lidos",
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError(
                "Nenhuma etiqueta de rastreio conhecida entre os códigos lidos"
            )

        # REGRA: mais de um pedido/destino encontrado = erro
        if len(pedidos_encontrados) > 1:
            codigos_match = [p.codigo_principal for p in pedidos_encontrados]
            rotas = list({p.rota_codigo for p in pedidos_encontrados})
            msg = (
                f"Múltiplos destinos encontrados nos códigos lidos: "
                f"etiquetas={codigos_match}, rotas={rotas}"
            )
            await self._log_sorter(
                tipo="consulta",
                payload_entrada=payload.model_dump(),
                sucesso=False,
                mensagem=msg,
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError(msg)

        pedido = pedidos_encontrados[0]
        codigo_encontrado = pedido.codigo_principal  # etiqueta de rastreio

        # Resolve saída pelo mapa habilitado e critério (sigla/uf/filial)
        saida_numero, valor_usado, criterio = await self._obter_saida_do_pedido(pedido)
        if saida_numero is None:
            msg = (
                f"Sem mapeamento para {criterio}='{valor_usado}' no mapa habilitado"
                if valor_usado
                else (criterio or "Nenhum mapa habilitado ou valor de destino ausente no pedido")
            )
            await self._log_sorter(
                tipo="consulta",
                payload_entrada=payload.model_dump(),
                codigo_encontrado=codigo_encontrado,
                sucesso=False,
                mensagem=msg,
                tempo_ms=int((time.perf_counter() - inicio) * 1000),
            )
            raise ValueError(msg)

        pedido.status = PedidoStatus.em_processamento
        pedido.processado_em = datetime.now(timezone.utc)

        response = ConsultaEtiquetaResponse(
            codigo=codigo_encontrado, saida=saida_numero
        )

        await self._log_sorter(
            tipo="consulta",
            payload_entrada=payload.model_dump(),
            payload_saida=response.model_dump(),
            codigo_encontrado=codigo_encontrado,
            saida_retornada=saida_numero,
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
            .order_by(Pedido.created_at.desc())
        )
        result = await self.db.execute(stmt)
        pedido = result.scalars().first()

        if not pedido:
            await self._log_sorter(
                tipo="confirmacao",
                payload_entrada=payload.model_dump(),
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

    async def _obter_saida_do_pedido(self, pedido) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Usa o mapa habilitado e seu critério (sigla|uf|filial)
        para achar a saída a partir dos dados do pedido.
        Retorna (saida_numero, valor_usado, criterio_ou_erro).
        """
        from app.models.rota import Mapa

        result = await self.db.execute(select(Mapa).where(Mapa.habilitado.is_(True)))
        mapa = result.scalar_one_or_none()
        if not mapa:
            return None, None, "Nenhum mapa habilitado"

        criterio = (
            mapa.criterio_roteamento.value
            if hasattr(mapa.criterio_roteamento, "value")
            else str(mapa.criterio_roteamento)
        )
        valor = None
        if criterio == "sigla":
            valor = pedido.sigla or pedido.rota_codigo
        elif criterio == "uf":
            valor = pedido.uf
        elif criterio == "filial":
            valor = pedido.filial

        if not valor:
            return None, None, f"Pedido sem valor para critério '{criterio}'"

        valor_norm = str(valor).strip()
        stmt = (
            select(Saida.numero)
            .join(MapeamentoRotaSaida, MapeamentoRotaSaida.saida_id == Saida.id)
            .where(
                and_(
                    MapeamentoRotaSaida.mapa_id == mapa.id,
                    MapeamentoRotaSaida.valor.ilike(valor_norm),
                    MapeamentoRotaSaida.ativo.is_(True),
                    Saida.ativo.is_(True),
                )
            )
            .order_by(MapeamentoRotaSaida.prioridade.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        saida = result.scalar_one_or_none()
        return saida, valor_norm, criterio

    async def _obter_saida_por_rota(self, rota_codigo: str) -> Optional[int]:
        """Compatibilidade: busca valor == rota_codigo no mapa habilitado."""
        from app.models.rota import Mapa

        stmt = (
            select(Saida.numero)
            .join(MapeamentoRotaSaida, MapeamentoRotaSaida.saida_id == Saida.id)
            .join(Mapa, Mapa.id == MapeamentoRotaSaida.mapa_id)
            .where(
                and_(
                    MapeamentoRotaSaida.valor.ilike(rota_codigo),
                    MapeamentoRotaSaida.ativo.is_(True),
                    Saida.ativo.is_(True),
                    Mapa.habilitado.is_(True),
                )
            )
            .order_by(MapeamentoRotaSaida.prioridade.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
