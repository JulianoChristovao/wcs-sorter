"""
Router de Pedidos (entrada do WMS + consultas da interface).
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_operador, require_gestor
from app.models.usuario import Usuario
from app.models.pedido import Pedido, PedidoStatus, PedidoEtiqueta, ConfirmacaoSorter
from app.models.log import LogIntegracaoWms
from app.schemas.pedido import PedidoCreate, PedidoResponse, PedidoListResponse
from app.services.wms_service import WmsService

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _to_response(pedido: Pedido, confirmacao: ConfirmacaoSorter | None = None) -> PedidoResponse:
    """
    Monta resposta sem disparar lazy-load (evita MissingGreenlet no async).
    Só usa confirmacoes se já estiverem no __dict__ (ex.: selectinload).
    """
    if confirmacao is None and "confirmacoes" in pedido.__dict__:
        confs = pedido.__dict__.get("confirmacoes") or []
        if confs:
            confirmacao = sorted(
                confs,
                key=lambda c: getattr(c, "created_at", None) or str(getattr(c, "id", "")),
                reverse=True,
            )[0]

    status_val = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)

    return PedidoResponse(
        id=pedido.id,
        codigo_externo=pedido.codigo_externo,
        etiqueta=pedido.codigo_principal,
        sigla=pedido.sigla,
        uf=pedido.uf,
        filial=pedido.filial,
        rota_codigo=pedido.rota_codigo,
        status=status_val,
        created_at=pedido.created_at,
        processado_em=pedido.processado_em,
        confirmado_em=pedido.confirmado_em,
        altura_cm=float(confirmacao.altura_cm) if confirmacao and confirmacao.altura_cm is not None else None,
        largura_cm=float(confirmacao.largura_cm) if confirmacao and confirmacao.largura_cm is not None else None,
        comprimento_cm=float(confirmacao.comprimento_cm) if confirmacao and confirmacao.comprimento_cm is not None else None,
        peso_kg=float(confirmacao.peso_kg) if confirmacao and confirmacao.peso_kg is not None else None,
        saida_confirmada=confirmacao.saida_numero if confirmacao else None,
    )


@router.post(
    "",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recebe pedido do WMS",
)
async def criar_pedido(
    payload: PedidoCreate,
    db: AsyncSession = Depends(get_db),
):
    service = WmsService(db)
    dados = payload.model_dump(by_alias=False)
    dados["etiqueta"] = payload.etiqueta
    dados["sigla"] = payload.sigla
    dados["uf"] = payload.uf
    dados["UF"] = payload.uf
    dados["filial"] = payload.filial
    dados["Filial"] = payload.filial
    dados["rota_codigo"] = payload.rota_codigo
    if payload.dados_extras:
        dados.update(payload.dados_extras)

    try:
        pedido = await service.receber_pedido(dados)
        await db.flush()
        # Não acessar relacionamentos aqui (MissingGreenlet). Campos escalares já estão no objeto.
        return _to_response(pedido, confirmacao=None)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gravar pedido: {type(exc).__name__}: {exc}",
        ) from exc


@router.get(
    "",
    response_model=PedidoListResponse,
    summary="Lista pedidos (com dados aferidos do sorter quando houver)",
)
async def listar_pedidos(
    status_filter: Optional[str] = Query(None, alias="status"),
    rota: Optional[str] = None,
    codigo: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    filters = []
    if status_filter:
        try:
            filters.append(Pedido.status == PedidoStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Status inválido")
    if rota:
        filters.append(Pedido.rota_codigo == rota.upper())
    if codigo:
        filters.append(Pedido.codigo_principal.ilike(f"%{codigo}%"))

    count_stmt = select(func.count()).select_from(Pedido)
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(Pedido)
        .options(selectinload(Pedido.confirmacoes))
        .order_by(Pedido.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    pedidos = result.scalars().all()

    return PedidoListResponse(
        total=total,
        page=page,
        size=size,
        items=[_to_response(p) for p in pedidos],
    )


@router.get("/{pedido_id}", response_model=PedidoResponse)
async def obter_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    result = await db.execute(
        select(Pedido)
        .options(selectinload(Pedido.confirmacoes))
        .where(Pedido.id == pedido_id)
    )
    pedido = result.scalar_one_or_none()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return _to_response(pedido)


@router.delete(
    "/{pedido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui pedido enviado pelo WMS",
    description=(
        "Remove o pedido e dados relacionados (etiquetas, confirmações, logs de integração). "
        "Não permite excluir se o status for 'separado' ou 'enviado_wms' (já processado), "
        "salvo com force=true."
    ),
)
async def excluir_pedido(
    pedido_id: UUID,
    force: bool = Query(
        False,
        description="Se true, permite excluir mesmo já separado/enviado ao WMS",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Pedido).where(Pedido.id == pedido_id))
    pedido = result.scalar_one_or_none()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    status_bloqueados = {PedidoStatus.separado, PedidoStatus.enviado_wms}
    if pedido.status in status_bloqueados and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Pedido com status '{pedido.status.value}' não pode ser excluído. "
                "Use force=true se realmente desejar remover."
            ),
        )

    # Remove dependências (logs, confirmações, etiquetas) antes do pedido
    await db.execute(delete(LogIntegracaoWms).where(LogIntegracaoWms.pedido_id == pedido_id))
    await db.execute(delete(ConfirmacaoSorter).where(ConfirmacaoSorter.pedido_id == pedido_id))
    await db.execute(delete(PedidoEtiqueta).where(PedidoEtiqueta.pedido_id == pedido_id))
    await db.delete(pedido)
