"""
Router do Dashboard (KPIs).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_operador
from app.models.usuario import Usuario
from app.models.pedido import Pedido, PedidoStatus
from app.models.log import LogSorter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _parse_dt(value: Optional[str], default: datetime) -> datetime:
    if not value:
        return default
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/kpis")
async def obter_kpis(
    inicio: Optional[str] = Query(
        None,
        description="Início do período (ISO 8601). Padrão: agora - 24h",
    ),
    fim: Optional[str] = Query(
        None,
        description="Fim do período (ISO 8601). Padrão: agora",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    agora = datetime.now(timezone.utc)
    fim_dt = _parse_dt(fim, agora)
    inicio_dt = _parse_dt(inicio, fim_dt - timedelta(hours=24))

    if inicio_dt > fim_dt:
        inicio_dt, fim_dt = fim_dt, inicio_dt

    # Pedidos por status (snapshot atual — fila operacional)
    stmt_status = select(Pedido.status, func.count()).group_by(Pedido.status)
    result_status = await db.execute(stmt_status)
    por_status = {row[0].value: row[1] for row in result_status.all()}

    pendentes = (
        por_status.get("pendente", 0)
        + por_status.get("recebido", 0)
        + por_status.get("em_processamento", 0)
    )

    # Separados no período (confirmado_em)
    stmt_sep = select(func.count()).where(
        and_(
            Pedido.status.in_([PedidoStatus.separado, PedidoStatus.enviado_wms]),
            Pedido.confirmado_em.is_not(None),
            Pedido.confirmado_em >= inicio_dt,
            Pedido.confirmado_em <= fim_dt,
        )
    )
    separados_periodo = (await db.execute(stmt_sep)).scalar_one() or 0

    # Consultas do sorter no período
    stmt_consultas = select(func.count()).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.created_at >= inicio_dt,
            LogSorter.created_at <= fim_dt,
        )
    )
    consultas_total = (await db.execute(stmt_consultas)).scalar_one() or 0

    stmt_ok = select(func.count()).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.sucesso.is_(True),
            LogSorter.created_at >= inicio_dt,
            LogSorter.created_at <= fim_dt,
        )
    )
    consultas_ok = (await db.execute(stmt_ok)).scalar_one() or 0

    stmt_erro = select(func.count()).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.sucesso.is_(False),
            LogSorter.created_at >= inicio_dt,
            LogSorter.created_at <= fim_dt,
        )
    )
    consultas_erro = (await db.execute(stmt_erro)).scalar_one() or 0

    if consultas_total < (consultas_ok + consultas_erro):
        consultas_total = consultas_ok + consultas_erro

    taxa_sucesso = (
        round((consultas_ok / consultas_total) * 100, 1) if consultas_total else 0.0
    )

    stmt_tempo = select(func.avg(LogSorter.tempo_ms)).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.tempo_ms.is_not(None),
            LogSorter.created_at >= inicio_dt,
            LogSorter.created_at <= fim_dt,
        )
    )
    tempo_medio = (await db.execute(stmt_tempo)).scalar_one()
    tempo_medio_ms = round(float(tempo_medio or 0), 1)

    return {
        "pendentes": pendentes,
        "separados_hoje": separados_periodo,  # compatível com frontend antigo
        "separados_periodo": separados_periodo,
        "por_status": por_status,
        "consultas_24h": consultas_total,  # total no período filtrado
        "consultas_ok_24h": consultas_ok,
        "consultas_erro_24h": consultas_erro,
        "taxa_sucesso_percent": taxa_sucesso,
        "tempo_medio_resposta_ms": tempo_medio_ms,
        "periodo_inicio": inicio_dt.isoformat(),
        "periodo_fim": fim_dt.isoformat(),
        "atualizado_em": agora.isoformat(),
    }
