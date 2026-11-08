"""
Serviço de integração com o WMS do cliente.
"""
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.pedido import Pedido, ConfirmacaoSorter, PedidoStatus, PedidoEtiqueta
from app.models.log import LogIntegracaoWms


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


class WmsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def receber_pedido(self, dados: dict[str, Any]) -> Pedido:
        """
        WMS envia pedido com etiqueta e destinos flexíveis.

        {
          "codigo_externo": "NF-111111111111111",
          "etiqueta": "FFFF45678",
          "sigla": "SAO",
          "UF": "SP",
          "Filial": "Braz"
        }
        """
        etiqueta = _norm(dados.get("etiqueta") or dados.get("codigo_principal"))
        if not etiqueta:
            raise ValueError("Campo 'etiqueta' é obrigatório")

        sigla = _norm(dados.get("sigla"))
        uf = _norm(dados.get("UF") or dados.get("uf"))
        filial = _norm(dados.get("Filial") or dados.get("filial"))
        rota_legado = _norm(dados.get("rota_codigo"))

        # rota_codigo: valor de display / fallback (preferência: sigla > uf > filial > rota)
        rota_codigo = sigla or uf or filial or rota_legado
        if not rota_codigo:
            raise ValueError("Informe ao menos um destino: sigla, UF, Filial ou rota_codigo")

        # Se só veio rota_codigo legado, grava também em sigla por compatibilidade
        if rota_legado and not sigla and not uf and not filial:
            sigla = rota_legado

        if uf:
            uf = uf.upper()
        if sigla:
            sigla = sigla.upper()

        pedido = Pedido(
            codigo_externo=_norm(dados.get("codigo_externo")),
            codigo_principal=etiqueta,
            rota_codigo=rota_codigo.upper() if rota_codigo else rota_codigo,
            sigla=sigla,
            uf=uf,
            filial=filial,
            dados_originais=dados,
            status=PedidoStatus.pendente,
            prioridade=int(dados.get("prioridade") or 5),
        )
        self.db.add(pedido)
        await self.db.flush()

        self.db.add(PedidoEtiqueta(pedido_id=pedido.id, codigo=etiqueta, tipo="rastreio"))

        self.db.add(
            LogIntegracaoWms(
                pedido_id=pedido.id,
                tipo="recebido",
                payload=dados,
                sucesso=True,
            )
        )
        return pedido

    async def notificar_separacao_concluida(
        self, pedido: Pedido, confirmacao: ConfirmacaoSorter
    ) -> bool:
        payload = {
            "pedido_id_wcs": str(pedido.id),
            "codigo_externo": pedido.codigo_externo,
            "etiqueta": pedido.codigo_principal,
            "sigla": pedido.sigla,
            "uf": pedido.uf,
            "filial": pedido.filial,
            "rota": pedido.rota_codigo,
            "status": "separado",
            "confirmacao": {
                "codigo": confirmacao.codigo,
                "altura_cm": float(confirmacao.altura_cm) if confirmacao.altura_cm else None,
                "largura_cm": float(confirmacao.largura_cm) if confirmacao.largura_cm else None,
                "comprimento_cm": float(confirmacao.comprimento_cm) if confirmacao.comprimento_cm else None,
                "peso_kg": float(confirmacao.peso_kg) if confirmacao.peso_kg else None,
                "saida": confirmacao.saida_numero,
                "timestamp": confirmacao.created_at.isoformat() if confirmacao.created_at else None,
            },
            "timestamp_wcs": datetime.now(timezone.utc).isoformat(),
        }

        sucesso = False
        resposta = None
        mensagem_erro = None

        if settings.WMS_WEBHOOK_URL:
            try:
                headers = {"Content-Type": "application/json"}
                if settings.WMS_API_KEY:
                    headers["X-API-Key"] = settings.WMS_API_KEY
                async with httpx.AsyncClient(timeout=settings.WMS_TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        settings.WMS_WEBHOOK_URL, json=payload, headers=headers
                    )
                    resposta = {"status_code": resp.status_code, "body": resp.text[:2000]}
                    sucesso = 200 <= resp.status_code < 300
                    if not sucesso:
                        mensagem_erro = f"WMS retornou status {resp.status_code}"
            except Exception as exc:
                mensagem_erro = str(exc)
                sucesso = False
        else:
            sucesso = True
            mensagem_erro = "WMS_WEBHOOK_URL não configurada – notificação simulada"

        if sucesso:
            pedido.status = PedidoStatus.enviado_wms

        log = LogIntegracaoWms(
            pedido_id=pedido.id,
            tipo="confirmacao_enviada" if sucesso else "confirmacao_erro",
            payload=payload,
            resposta=resposta,
            sucesso=sucesso,
            mensagem_erro=mensagem_erro,
        )
        self.db.add(log)
        await self.db.flush()
        # Garante que log de falha não suma se houver rollback posterior
        if not sucesso:
            await self.db.commit()
        return sucesso
