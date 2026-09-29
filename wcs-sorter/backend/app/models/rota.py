"""
Modelos de Mapa, Rota, Saída e Mapeamento.
"""
from datetime import datetime
import enum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CriterioRoteamento(str, enum.Enum):
    sigla = "sigla"
    uf = "uf"
    filial = "filial"


class Mapa(Base):
    """
    Conjunto de mapeamentos valor → saída.
    Apenas um mapa habilitado por vez.
    Cada mapa trabalha com UM critério: sigla, uf ou filial.
    """
    __tablename__ = "mapas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    quantidade_saidas: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    criterio_roteamento: Mapped[CriterioRoteamento] = mapped_column(
        Enum(
            CriterioRoteamento,
            name="criterio_roteamento",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CriterioRoteamento.sigla,
    )
    habilitado: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    mapeamentos = relationship(
        "MapeamentoRotaSaida", back_populates="mapa", cascade="all, delete-orphan"
    )


class ConfigSorter(Base):
    __tablename__ = "config_sorter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quantidade_saidas: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))


class Saida(Base):
    __tablename__ = "saidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(100))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    mapeamentos = relationship("MapeamentoRotaSaida", back_populates="saida")


class Rota(Base):
    """Catálogo opcional de valores de roteamento."""
    __tablename__ = "rotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(150), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mapeamentos = relationship("MapeamentoRotaSaida", back_populates="rota")


class MapeamentoRotaSaida(Base):
    """Mapeia um valor (sigla/UF/filial conforme o critério do mapa) para uma saída."""
    __tablename__ = "mapeamento_rota_saida"
    __table_args__ = (
        UniqueConstraint("mapa_id", "valor", name="uq_mapa_valor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mapa_id: Mapped[int] = mapped_column(
        ForeignKey("mapas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valor: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rota_id: Mapped[int | None] = mapped_column(
        ForeignKey("rotas.id", ondelete="SET NULL"), nullable=True
    )
    saida_id: Mapped[int] = mapped_column(ForeignKey("saidas.id", ondelete="CASCADE"), nullable=False)
    prioridade: Mapped[int] = mapped_column(Integer, default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    mapa = relationship("Mapa", back_populates="mapeamentos")
    rota = relationship("Rota", back_populates="mapeamentos")
    saida = relationship("Saida", back_populates="mapeamentos")
