"""
Router do Dashboard (KPIs).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_operador
from app.models.usuario import Usuario
from app.models.pedido import Pedido, PedidoStatus
from app.models.log import LogSorter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/kpis")
async def obter_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    agora = datetime.now(timezone.utc)
    inicio_hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    # Pedidos por status
    stmt_status = (
        select(Pedido.status, func.count())
        .group_by(Pedido.status)
    )
    result_status = await db.execute(stmt_status)
    por_status = {row[0].value: row[1] for row in result_status.all()}

    # Separados hoje
    stmt_hoje = select(func.count()).where(
        and_(
            Pedido.status.in_([PedidoStatus.separado, PedidoStatus.enviado_wms]),
            Pedido.confirmado_em >= inicio_hoje,
        )
    )
    separados_hoje = (await db.execute(stmt_hoje)).scalar_one()

    # Pendentes
    pendentes = por_status.get("pendente", 0) + por_status.get("recebido", 0) + por_status.get("em_processamento", 0)

    # Consultas do sorter nas últimas 24h
    stmt_consultas = select(func.count()).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.created_at >= agora - timedelta(hours=24),
        )
    )
    consultas_24h = (await db.execute(stmt_consultas)).scalar_one()

    # Taxa de sucesso das consultas (24h)
    stmt_sucesso = select(func.count()).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.sucesso.is_(True),
            LogSorter.created_at >= agora - timedelta(hours=24),
        )
    )
    consultas_ok = (await db.execute(stmt_sucesso)).scalar_one()
    taxa_sucesso = round((consultas_ok / consultas_24h * 100) if consultas_24h else 100, 1)

    # Tempo médio de resposta do sorter (ms)
    stmt_tempo = select(func.avg(LogSorter.tempo_ms)).where(
        and_(
            LogSorter.tipo == "consulta",
            LogSorter.tempo_ms.is_not(None),
            LogSorter.created_at >= agora - timedelta(hours=24),
        )
    )
    tempo_medio = (await db.execute(stmt_tempo)).scalar_one()
    tempo_medio_ms = round(float(tempo_medio or 0), 1)

    return {
        "pendentes": pendentes,
        "separados_hoje": separados_hoje,
        "por_status": por_status,
        "consultas_24h": consultas_24h,
        "taxa_sucesso_percent": taxa_sucesso,
        "tempo_medio_resposta_ms": tempo_medio_ms,
        "atualizado_em": agora.isoformat(),
    }