"""
Router de gestão de usuários.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash, require_gestor, require_admin
from app.models.usuario import Usuario, UserRole
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("", response_model=list[UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Usuario).order_by(Usuario.username))
    return result.scalars().all()


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    payload: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    # Apenas admin pode criar outro admin
    if payload.role == "admin" and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar usuários admin",
        )

    exists = await db.execute(
        select(Usuario).where(
            (Usuario.username == payload.username) | (Usuario.email == payload.email)
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username ou e-mail já cadastrado")

    user = Usuario(
        username=payload.username,
        email=payload.email,
        nome_completo=payload.nome_completo,
        password_hash=get_password_hash(payload.password),
        role=UserRole(payload.role),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    user_id: UUID,
    payload: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_gestor),
):
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if payload.role == "admin" and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem definir papel admin",
        )

    if payload.email is not None:
        user.email = payload.email
    if payload.nome_completo is not None:
        user.nome_completo = payload.nome_completo
    if payload.password is not None:
        user.password_hash = get_password_hash(payload.password)
    if payload.role is not None:
        user.role = UserRole(payload.role)
    if payload.ativo is not None:
        user.ativo = payload.ativo

    await db.flush()
    await db.refresh(user)
    return user