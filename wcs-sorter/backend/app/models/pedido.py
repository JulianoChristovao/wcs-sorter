"""
Modelos de Pedido, Etiquetas e Confirmações.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PedidoStatus(str, enum.Enum):
    recebido = "recebido"
    pendente = "pendente"
    em_processamento = "em_processamento"
    separado = "separado"
    enviado_wms = "enviado_wms"
    erro = "erro"
    cancelado = "cancelado"


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    codigo_externo: Mapped[str | None] = mapped_column(String(100))
    codigo_principal: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rota_codigo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # valor usado no roteamento (legado/display)
    sigla: Mapped[str | None] = mapped_column(String(50), index=True)
    uf: Mapped[str | None] = mapped_column(String(10), index=True)
    filial: Mapped[str | None] = mapped_column(String(100), index=True)
    dados_originais: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[PedidoStatus] = mapped_column(
        Enum(
            PedidoStatus,
            name="pedido_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PedidoStatus.pendente,
        index=True,
    )
    prioridade: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    etiquetas = relationship("PedidoEtiqueta", back_populates="pedido", cascade="all, delete-orphan")
    confirmacoes = relationship("ConfirmacaoSorter", back_populates="pedido")


class PedidoEtiqueta(Base):
    __tablename__ = "pedido_etiquetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(50), default="barcode")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    pedido = relationship("Pedido", back_populates="etiquetas")


class ConfirmacaoSorter(Base):
    __tablename__ = "confirmacoes_sorter"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id"), nullable=False, index=True
    )
    codigo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    altura_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    largura_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    comprimento_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    peso_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    saida_numero: Mapped[int] = mapped_column(Integer, nullable=False)
    dados_brutos: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    pedido = relationship("Pedido", back_populates="confirmacoes")