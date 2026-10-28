"""
Consulta de logs do sorter e da integração WMS.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.models.usuario import Usuario
from app.models.log import LogSorter, LogIntegracaoWms
from app.schemas.logs import LogSorterResponse, LogWmsResponse, LogsPage

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/sorter", response_model=LogsPage[LogSorterResponse])
async def listar_logs_sorter(
    sucesso: Optional[bool] = None,
    tipo: Optional[str] = None,
    codigo: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    filters = []
    if sucesso is not None:
        filters.append(LogSorter.sucesso.is_(sucesso))
    if tipo:
        filters.append(LogSorter.tipo == tipo)
    if codigo:
        filters.append(LogSorter.codigo_encontrado.ilike(f"%{codigo}%"))

    count_q = select(LogSorter)
    if filters:
        for f in filters:
            count_q = count_q.where(f)
    # count
    from sqlalchemy import func

    total = (
        await db.execute(select(func.count()).select_from(count_q.subquery()))
    ).scalar_one()

    stmt = select(LogSorter).order_by(desc(LogSorter.created_at)).offset((page - 1) * size).limit(size)
    for f in filters:
        stmt = stmt.where(f)
    rows = (await db.execute(stmt)).scalars().all()

    return LogsPage(
        total=total,
        page=page,
        size=size,
        items=[
            LogSorterResponse(
                id=str(r.id),
                tipo=r.tipo,
                codigo_encontrado=r.codigo_encontrado,
                saida_retornada=r.saida_retornada,
                tempo_ms=r.tempo_ms,
                sucesso=r.sucesso,
                mensagem=r.mensagem,
                payload_entrada=r.payload_entrada,
                payload_saida=r.payload_saida,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


@router.get("/wms", response_model=LogsPage[LogWmsResponse])
async def listar_logs_wms(
    sucesso: Optional[bool] = None,
    tipo: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    from sqlalchemy import func

    filters = []
    if sucesso is not None:
        filters.append(LogIntegracaoWms.sucesso.is_(sucesso))
    if tipo:
        filters.append(LogIntegracaoWms.tipo == tipo)

    base = select(LogIntegracaoWms)
    for f in filters:
        base = base.where(f)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = (
        select(LogIntegracaoWms)
        .order_by(desc(LogIntegracaoWms.created_at))
        .offset((page - 1) * size)
        .limit(size)
    )
    for f in filters:
        stmt = stmt.where(f)
    rows = (await db.execute(stmt)).scalars().all()

    return LogsPage(
        total=total,
        page=page,
        size=size,
        items=[
            LogWmsResponse(
                id=str(r.id),
                pedido_id=str(r.pedido_id) if r.pedido_id else None,
                tipo=r.tipo,
                sucesso=r.sucesso,
                mensagem_erro=r.mensagem_erro,
                payload=r.payload,
                resposta=r.resposta,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )
