"""
Modelos de Logs e Auditoria.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogIntegracaoWms(Base):
    __tablename__ = "log_integracao_wms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pedidos.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    resposta: Mapped[dict | None] = mapped_column(JSONB)
    sucesso: Mapped[bool | None] = mapped_column(Boolean)
    mensagem_erro: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class LogSorter(Base):
    __tablename__ = "log_sorter"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_entrada: Mapped[dict | None] = mapped_column(JSONB)
    payload_saida: Mapped[dict | None] = mapped_column(JSONB)
    codigo_encontrado: Mapped[str | None] = mapped_column(String(100), index=True)
    saida_retornada: Mapped[int | None] = mapped_column(Integer)
    tempo_ms: Mapped[int | None] = mapped_column(Integer)
    sucesso: Mapped[bool] = mapped_column(Boolean, default=True)
    mensagem: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True
    )
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    tabela: Mapped[str | None] = mapped_column(String(50))
    registro_id: Mapped[str | None] = mapped_column(String(100))
    dados_anteriores: Mapped[dict | None] = mapped_column(JSONB)
    dados_novos: Mapped[dict | None] = mapped_column(JSONB)
    ip_origem: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )