"""
Popula dados de demonstração para apresentação do TCC.
Uso: docker compose exec api python -m scripts.seed_demo
"""
import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.rota import Mapa, Rota, Saida, MapeamentoRotaSaida
from app.models.pedido import Pedido, PedidoEtiqueta, PedidoStatus
from app.services.wms_service import WmsService


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Garante mapa demo offline + mapeamentos diferentes do padrão
        result = await db.execute(select(Mapa).where(Mapa.nome == "Turno noite"))
        mapa_noite = result.scalar_one_or_none()
        if not mapa_noite:
            mapa_noite = Mapa(
                nome="Turno noite",
                descricao="Mapa alternativo para demonstração",
                quantidade_saidas=6,
                habilitado=False,
            )
            db.add(mapa_noite)
            await db.flush()
            print(f"Mapa criado: {mapa_noite.nome} (id={mapa_noite.id})")
        else:
            print(f"Mapa já existe: {mapa_noite.nome}")

        # Saídas 1..6
        for num in range(1, 7):
            r = await db.execute(select(Saida).where(Saida.numero == num))
            if not r.scalar_one_or_none():
                db.add(Saida(numero=num, descricao=f"Saída {num}"))
        await db.flush()

        # Rotas
        rotas_demo = [
            ("SAO", "São Paulo"),
            ("CWB", "Curitiba"),
            ("RIO", "Rio de Janeiro"),
        ]
        rota_ids = {}
        for cod, desc in rotas_demo:
            r = await db.execute(select(Rota).where(Rota.codigo == cod))
            rota = r.scalar_one_or_none()
            if not rota:
                rota = Rota(codigo=cod, descricao=desc)
                db.add(rota)
                await db.flush()
            rota_ids[cod] = rota.id

        # Mapeamento no mapa noite: SAO->2, CWB->4, RIO->6 (diferente do padrão)
        saida_por_rota = {"SAO": 2, "CWB": 4, "RIO": 6}
        for cod, saida_num in saida_por_rota.items():
            rs = await db.execute(select(Saida).where(Saida.numero == saida_num))
            saida = rs.scalar_one()
            existing = await db.execute(
                select(MapeamentoRotaSaida).where(
                    MapeamentoRotaSaida.mapa_id == mapa_noite.id,
                    MapeamentoRotaSaida.rota_id == rota_ids[cod],
                    MapeamentoRotaSaida.ativo.is_(True),
                )
            )
            if not existing.scalars().first():
                db.add(
                    MapeamentoRotaSaida(
                        mapa_id=mapa_noite.id,
                        rota_id=rota_ids[cod],
                        saida_id=saida.id,
                    )
                )

        # Pedidos de exemplo
        service = WmsService(db)
        pedidos_demo = [
            {"codigo_externo": "NF-DEMO-001", "etiqueta": "TRK0001", "rota_codigo": "SAO"},
            {"codigo_externo": "NF-DEMO-002", "etiqueta": "TRK0002", "rota_codigo": "CWB"},
            {"codigo_externo": "NF-DEMO-003", "etiqueta": "TRK0003", "rota_codigo": "RIO"},
        ]
        for p in pedidos_demo:
            exists = await db.execute(
                select(Pedido).where(Pedido.codigo_principal == p["etiqueta"])
            )
            if not exists.scalar_one_or_none():
                await service.receber_pedido(p)
                print(f"Pedido criado: {p['etiqueta']} → {p['rota_codigo']}")
            else:
                print(f"Pedido já existe: {p['etiqueta']}")

        await db.commit()
        print("Seed demo concluído.")


if __name__ == "__main__":
    asyncio.run(main())
