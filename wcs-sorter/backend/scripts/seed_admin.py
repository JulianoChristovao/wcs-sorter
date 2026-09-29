"""
Script para criar/atualizar o usuário admin com hash bcrypt compatível com a aplicação.
Execute após o banco estar no ar:

    docker compose exec api python -m scripts.seed_admin
"""
import asyncio
import sys
sys.path.insert(0, "/app")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.usuario import Usuario, UserRole


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario).where(Usuario.username == "admin"))
        user = result.scalar_one_or_none()

        password_hash = get_password_hash("Admin@123")

        if user:
            user.password_hash = password_hash
            user.ativo = True
            print("Usuário admin atualizado com sucesso.")
        else:
            user = Usuario(
                username="admin",
                email="admin@wcs.local",
                nome_completo="Administrador do Sistema",
                password_hash=password_hash,
                role=UserRole.admin,
            )
            db.add(user)
            print("Usuário admin criado com sucesso.")

        await db.commit()
        print("Login: admin / Admin@123")


if __name__ == "__main__":
    asyncio.run(main())