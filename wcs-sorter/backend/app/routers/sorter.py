"""
APIs machine-to-machine do Sorter.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_sorter_api_key
from app.schemas.sorter import (
    ConsultaEtiquetaRequest,
    ConsultaEtiquetaResponse,
    ConfirmacaoSorterRequest,
    ConfirmacaoSorterResponse,
)
from app.services.sorter_service import SorterService

router = APIRouter(prefix="/sorter", tags=["Sorter (Automação)"])


@router.post(
    "/consultar",
    response_model=ConsultaEtiquetaResponse,
    summary="Consulta código e rampa de destino",
    description=(
        "O sorter lê **todos** os códigos de barras da caixa e envia separados por `;`.\n\n"
        "O WCS identifica qual deles é a etiqueta de rastreio de um pedido pendente "
        "e retorna o código + a saída mapeada.\n\n"
        "**Regra:** se mais de um código corresponder a pedidos com destino, "
        "retorna erro 409 (múltiplos destinos)."
    ),
)
async def consultar_etiqueta(
    payload: ConsultaEtiquetaRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_sorter_api_key),
):
    service = SorterService(db)
    try:
        return await service.consultar_etiqueta(payload)
    except ValueError as exc:
        msg = str(exc)
        # Múltiplos destinos → 409 Conflict
        if "Múltiplos destinos" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        # Não encontrado → 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)


@router.post(
    "/confirmar",
    response_model=ConfirmacaoSorterResponse,
    summary="Confirma separação com dados aferidos",
    description=(
        "Após a separação física, o sorter envia o código (etiqueta de rastreio), "
        "medidas e a saída utilizada. O WCS grava a confirmação e notifica o WMS."
    ),
)
async def confirmar_separacao(
    payload: ConfirmacaoSorterRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_sorter_api_key),
):
    service = SorterService(db)
    try:
        return await service.confirmar_separacao(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
