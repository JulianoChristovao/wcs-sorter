"""
Router de Mapas, Rotas, Saídas e Mapeamento.
Apenas o mapa com habilitado=True direciona o sorter.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_operador, require_gestor, require_admin
from app.models.usuario import Usuario
from app.models.rota import Mapa, Rota, Saida, MapeamentoRotaSaida, ConfigSorter, CriterioRoteamento
from app.schemas.mapeamento import (
    MapaCreate,
    MapaUpdate,
    MapaResponse,
    RotaCreate,
    RotaResponse,
    SaidaResponse,
    MapeamentoCreate,
    MapeamentoResponse,
    ConfigSorterUpdate,
    ConfigSorterResponse,
)

router = APIRouter(prefix="/mapeamento", tags=["Mapeamento de Rotas"])


async def _garantir_saidas(db: AsyncSession, quantidade: int) -> None:
    result = await db.execute(select(Saida.numero))
    existentes = {row[0] for row in result.all()}
    for num in range(1, quantidade + 1):
        if num not in existentes:
            db.add(Saida(numero=num, descricao=f"Saída {num}"))
    await db.execute(
        update(Saida).where(Saida.numero > quantidade).values(ativo=False)
    )
    await db.execute(
        update(Saida).where(Saida.numero <= quantidade).values(ativo=True)
    )


async def _desabilitar_outros_mapas(db: AsyncSession, exceto_id: int | None = None) -> None:
    stmt = update(Mapa).values(habilitado=False)
    if exceto_id is not None:
        stmt = stmt.where(Mapa.id != exceto_id)
    await db.execute(stmt)


# ---------- Mapas ----------
@router.get("/mapas", response_model=list[MapaResponse])
async def listar_mapas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    result = await db.execute(select(Mapa).order_by(Mapa.nome))
    return result.scalars().all()


@router.get("/mapas/ativo", response_model=MapaResponse)
async def obter_mapa_ativo(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    result = await db.execute(select(Mapa).where(Mapa.habilitado.is_(True)))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Nenhum mapa habilitado")
    return mapa


@router.post("/mapas", response_model=MapaResponse, status_code=status.HTTP_201_CREATED)
async def criar_mapa(
    payload: MapaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    if payload.habilitado:
        await _desabilitar_outros_mapas(db)

    mapa = Mapa(
        nome=payload.nome,
        descricao=payload.descricao,
        quantidade_saidas=payload.quantidade_saidas,
        criterio_roteamento=CriterioRoteamento(payload.criterio_roteamento),
        habilitado=payload.habilitado,
        updated_by=current_user.id,
    )
    db.add(mapa)
    await db.flush()
    await _garantir_saidas(db, payload.quantidade_saidas)
    await db.refresh(mapa)
    return mapa


@router.patch("/mapas/{mapa_id}", response_model=MapaResponse)
async def atualizar_mapa(
    mapa_id: int,
    payload: MapaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Mapa).where(Mapa.id == mapa_id))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa não encontrado")

    if payload.nome is not None:
        mapa.nome = payload.nome
    if payload.descricao is not None:
        mapa.descricao = payload.descricao
    if payload.quantidade_saidas is not None:
        mapa.quantidade_saidas = payload.quantidade_saidas
        await _garantir_saidas(db, payload.quantidade_saidas)
    mapa.updated_by = current_user.id
    await db.flush()
    await db.refresh(mapa)
    return mapa


@router.post("/mapas/{mapa_id}/habilitar", response_model=MapaResponse)
async def habilitar_mapa(
    mapa_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    """Habilita este mapa e desabilita todos os outros. Só o habilitado direciona o sorter."""
    result = await db.execute(select(Mapa).where(Mapa.id == mapa_id))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa não encontrado")

    await _desabilitar_outros_mapas(db, exceto_id=mapa_id)
    mapa.habilitado = True
    mapa.updated_by = current_user.id
    await _garantir_saidas(db, mapa.quantidade_saidas)
    await db.flush()
    await db.refresh(mapa)
    return mapa


@router.post("/mapas/{mapa_id}/desabilitar", response_model=MapaResponse)
async def desabilitar_mapa(
    mapa_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Mapa).where(Mapa.id == mapa_id))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa não encontrado")

    mapa.habilitado = False
    mapa.updated_by = current_user.id
    await db.flush()
    await db.refresh(mapa)
    return mapa


@router.delete("/mapas/{mapa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_mapa(
    mapa_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Mapa).where(Mapa.id == mapa_id))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa não encontrado")
    if mapa.habilitado:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir o mapa habilitado. Desabilite-o ou habilite outro antes.",
        )
    await db.delete(mapa)


# ---------- Config legada (usa mapa ativo se existir) ----------
@router.get("/config", response_model=ConfigSorterResponse)
async def obter_config(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    result = await db.execute(select(Mapa).where(Mapa.habilitado.is_(True)))
    mapa = result.scalar_one_or_none()
    if mapa:
        return ConfigSorterResponse(
            id=mapa.id,
            quantidade_saidas=mapa.quantidade_saidas,
            descricao=f"Mapa ativo: {mapa.nome}",
            ativo=True,
            updated_at=mapa.updated_at,
        )
    result = await db.execute(
        select(ConfigSorter).where(ConfigSorter.ativo.is_(True)).order_by(ConfigSorter.id.desc())
    )
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Nenhuma configuração / mapa ativo")
    return config


@router.put("/config", response_model=ConfigSorterResponse)
async def atualizar_config(
    payload: ConfigSorterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    """Atualiza quantidade de saídas do mapa habilitado."""
    result = await db.execute(select(Mapa).where(Mapa.habilitado.is_(True)))
    mapa = result.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Nenhum mapa habilitado para configurar")
    mapa.quantidade_saidas = payload.quantidade_saidas
    if payload.descricao:
        mapa.descricao = payload.descricao
    mapa.updated_by = current_user.id
    await _garantir_saidas(db, payload.quantidade_saidas)
    await db.flush()
    await db.refresh(mapa)
    return ConfigSorterResponse(
        id=mapa.id,
        quantidade_saidas=mapa.quantidade_saidas,
        descricao=mapa.descricao,
        ativo=True,
        updated_at=mapa.updated_at,
    )


# ---------- Saídas ----------
@router.get("/saidas", response_model=list[SaidaResponse])
async def listar_saidas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    result = await db.execute(
        select(Saida).where(Saida.ativo.is_(True)).order_by(Saida.numero)
    )
    return result.scalars().all()


# ---------- Rotas (catálogo de siglas — independente do mapeamento no mapa) ----------
@router.get("/rotas", response_model=list[RotaResponse])
async def listar_rotas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    """Lista apenas siglas ativas do catálogo."""
    result = await db.execute(
        select(Rota).where(Rota.ativo.is_(True)).order_by(Rota.codigo)
    )
    return result.scalars().all()


@router.post("/rotas", response_model=RotaResponse, status_code=status.HTTP_201_CREATED)
async def criar_rota(
    payload: RotaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    """
    Cadastra sigla no catálogo.
    Se já existia inativa (foi excluída), reativa e atualiza a descrição.
    NÃO cria mapeamento em nenhum mapa.
    """
    codigo = payload.codigo.strip().upper()
    if not codigo:
        raise HTTPException(status_code=400, detail="Código da rota é obrigatório")

    result = await db.execute(select(Rota).where(Rota.codigo == codigo))
    existente = result.scalar_one_or_none()

    if existente:
        if existente.ativo:
            raise HTTPException(status_code=400, detail="Código de rota já existe")
        # Reativa registro previamente excluído
        existente.ativo = True
        existente.descricao = payload.descricao
        await db.flush()
        await db.refresh(existente)
        return existente

    rota = Rota(codigo=codigo, descricao=payload.descricao, ativo=True)
    db.add(rota)
    await db.flush()
    await db.refresh(rota)
    return rota


@router.delete("/rotas/{rota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_rota(
    rota_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    """
    Remove sigla do catálogo (soft-delete).
    Não remove mapeamentos já feitos nos mapas — apenas desvincula a descrição do catálogo.
    """
    result = await db.execute(select(Rota).where(Rota.id == rota_id))
    rota = result.scalar_one_or_none()
    if not rota:
        raise HTTPException(status_code=404, detail="Rota não encontrada")
    rota.ativo = False
    await db.flush()



@router.get("/mapas/{mapa_id}/mapeamentos", response_model=list[MapeamentoResponse])
async def listar_mapeamentos_do_mapa(
    mapa_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    """Lista mapeamentos de um mapa específico."""
    result_mapa = await db.execute(select(Mapa).where(Mapa.id == mapa_id))
    if not result_mapa.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Mapa não encontrado")

    stmt = (
        select(MapeamentoRotaSaida)
        .options(
            selectinload(MapeamentoRotaSaida.rota),
            selectinload(MapeamentoRotaSaida.saida),
        )
        .where(
            and_(
                MapeamentoRotaSaida.mapa_id == mapa_id,
                MapeamentoRotaSaida.ativo.is_(True),
            )
        )
        .order_by(MapeamentoRotaSaida.id)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        MapeamentoResponse(
            id=m.id,
            mapa_id=m.mapa_id,
            valor=m.valor,
            rota_codigo=m.rota.codigo if m.rota else m.valor,
            rota_descricao=m.rota.descricao if m.rota else m.valor,
            saida_numero=m.saida.numero,
            saida_descricao=m.saida.descricao,
            ativo=m.ativo,
        )
        for m in items
    ]


# ---------- Mapeamentos (por mapa) ----------
@router.get("", response_model=list[MapeamentoResponse])
async def listar_mapeamentos(
    mapa_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_operador),
):
    """Lista mapeamentos. Se mapa_id não for informado, usa o mapa habilitado."""
    if mapa_id is None:
        result = await db.execute(select(Mapa).where(Mapa.habilitado.is_(True)))
        mapa = result.scalar_one_or_none()
        if not mapa:
            return []
        mapa_id = mapa.id

    stmt = (
        select(MapeamentoRotaSaida)
        .options(
            selectinload(MapeamentoRotaSaida.rota),
            selectinload(MapeamentoRotaSaida.saida),
        )
        .where(
            and_(
                MapeamentoRotaSaida.mapa_id == mapa_id,
                MapeamentoRotaSaida.ativo.is_(True),
            )
        )
        .order_by(MapeamentoRotaSaida.id)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        MapeamentoResponse(
            id=m.id,
            mapa_id=m.mapa_id,
            valor=m.valor,
            rota_codigo=m.rota.codigo if m.rota else m.valor,
            rota_descricao=m.rota.descricao if m.rota else m.valor,
            saida_numero=m.saida.numero,
            saida_descricao=m.saida.descricao,
            ativo=m.ativo,
        )
        for m in items
    ]


@router.post("", response_model=MapeamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_ou_atualizar_mapeamento(
    payload: MapeamentoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result_mapa = await db.execute(select(Mapa).where(Mapa.id == payload.mapa_id))
    mapa = result_mapa.scalar_one_or_none()
    if not mapa:
        raise HTTPException(status_code=404, detail="Mapa não encontrado")

    valor = (payload.valor or payload.rota_codigo or "").strip()
    if not valor:
        raise HTTPException(status_code=400, detail="Campo 'valor' é obrigatório")

    # Normaliza conforme critério
    criterio = (
        mapa.criterio_roteamento.value
        if hasattr(mapa.criterio_roteamento, "value")
        else str(mapa.criterio_roteamento)
    )
    if criterio in ("sigla", "uf"):
        valor = valor.upper()

    result_saida = await db.execute(
        select(Saida).where(
            and_(Saida.numero == payload.saida_numero, Saida.ativo.is_(True))
        )
    )
    saida = result_saida.scalar_one_or_none()
    if not saida:
        raise HTTPException(status_code=404, detail="Saída não encontrada ou inativa")

    if payload.saida_numero > mapa.quantidade_saidas:
        raise HTTPException(
            status_code=400,
            detail=f"Saída {payload.saida_numero} acima do limite do mapa ({mapa.quantidade_saidas})",
        )

    # Catálogo: NUNCA cria rota aqui.
    # Se o mapa for por SIGLA, o valor precisa existir no cadastro de siglas.
    result_rota = await db.execute(
        select(Rota).where(and_(Rota.codigo == valor, Rota.ativo.is_(True)))
    )
    rota = result_rota.scalar_one_or_none()

    if criterio == "sigla" and rota is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sigla '{valor}' não existe no cadastro de siglas. "
                "Cadastre-a primeiro em 'Cadastro de siglas' e depois mapeie no mapa."
            ),
        )

    result_existente = await db.execute(
        select(MapeamentoRotaSaida).where(
            and_(
                MapeamentoRotaSaida.mapa_id == mapa.id,
                MapeamentoRotaSaida.valor.ilike(valor),
                MapeamentoRotaSaida.ativo.is_(True),
            )
        )
    )
    existente = result_existente.scalars().first()

    if existente:
        existente.saida_id = saida.id
        existente.valor = valor
        existente.rota_id = rota.id if rota else existente.rota_id
        existente.updated_by = current_user.id
        mapeamento = existente
    else:
        mapeamento = MapeamentoRotaSaida(
            mapa_id=mapa.id,
            valor=valor,
            rota_id=rota.id if rota else None,
            saida_id=saida.id,
            updated_by=current_user.id,
        )
        db.add(mapeamento)

    await db.flush()
    await db.refresh(mapeamento)

    return MapeamentoResponse(
        id=mapeamento.id,
        mapa_id=mapa.id,
        valor=valor,
        rota_codigo=rota.codigo if rota else valor,
        rota_descricao=rota.descricao if rota else valor,
        saida_numero=saida.numero,
        saida_descricao=saida.descricao,
        ativo=mapeamento.ativo,
    )


@router.delete("/{mapeamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_mapeamento(
    mapeamento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    """Remove definitivamente o mapeamento valor → saída do mapa."""
    result = await db.execute(
        select(MapeamentoRotaSaida).where(MapeamentoRotaSaida.id == mapeamento_id)
    )
    mapeamento = result.scalar_one_or_none()
    if not mapeamento:
        raise HTTPException(status_code=404, detail="Mapeamento não encontrado")
    await db.delete(mapeamento)
    await db.flush()
