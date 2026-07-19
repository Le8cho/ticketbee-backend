"""
Inicializa el schema en la base de datos NUEVA del ambiente de Azure personal
(techfix-infra/, ver /home/le8cho/.claude/plans/happy-tinkering-puffin.md, Paso 4).

No toca la base de datos de desarrollo local (la de .env) — lee la cadena de
conexión de AZURE_DATABASE_URL, a propósito con un nombre distinto a
DATABASE_URL para que no haya forma de confundirlas.

Uso:
    AZURE_DATABASE_URL="$(az keyvault secret show --vault-name kv-techfix-2026 \
        --name database-url --query value -o tsv)" \
        uv run python scripts/init_azure_infra_schema.py
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import Base

# Importar TODOS los modelos para que queden registrados en Base.metadata —
# app/models/__init__.py no incluye Pago, hay que importarlo aparte a mano.
from app.models.tipo_dispositivo import TipoDispositivo
from app.models.tecnico import Tecnico  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.dispositivo import Dispositivo  # noqa: F401
from app.models.servicio import Servicio
from app.models.ticket import Ticket  # noqa: F401
from app.models.adjunto import Adjunto  # noqa: F401
from app.models.garantia import Garantia  # noqa: F401
from app.models.pago import Pago  # noqa: F401

SCHEMAS = ("owner", "clientes", "pagos")

CATALOGO_TIPO_DISPOSITIVO = ["Laptop", "PC de Escritorio", "Celular", "Tablet"]

CATALOGO_SERVICIO = [
    {"nombre": "Diagnóstico general", "tipo_servicio": "PREVENTIVO", "precio_base": 30.00},
    {"nombre": "Cambio de pantalla", "tipo_servicio": "CORRECTIVO", "precio_base": 150.00},
    {"nombre": "Limpieza y mantenimiento", "tipo_servicio": "PREVENTIVO", "precio_base": 40.00},
    {"nombre": "Reparación de placa", "tipo_servicio": "CORRECTIVO", "precio_base": 200.00},
    {"nombre": "Otro / Diagnóstico personalizado", "tipo_servicio": "OTROS", "precio_base": 0.01},
]


async def crear_schemas(engine) -> None:
    async with engine.begin() as conn:
        for schema in SCHEMAS:
            # CREATE SCHEMA tiene que ser la única sentencia de su batch en SQL Server —
            # por eso va envuelto en EXEC() de SQL dinámico.
            await conn.execute(
                text(
                    f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') "
                    f"EXEC('CREATE SCHEMA {schema}')"
                )
            )
    print(f"Schemas verificados/creados: {', '.join(SCHEMAS)}")


async def crear_tablas(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tablas creadas (o ya existentes) a partir de los modelos de SQLAlchemy.")


async def sembrar_catalogo(engine) -> None:
    async with AsyncSession(engine) as session:
        tipos_existentes = (await session.execute(select(TipoDispositivo))).scalars().all()
        if tipos_existentes:
            print(f"TipoDispositivo ya tiene {len(tipos_existentes)} fila(s), no se siembra de nuevo.")
        else:
            session.add_all([TipoDispositivo(nombre=n) for n in CATALOGO_TIPO_DISPOSITIVO])
            print(f"Catálogo TipoDispositivo sembrado ({len(CATALOGO_TIPO_DISPOSITIVO)} filas).")

        servicios_existentes = (await session.execute(select(Servicio))).scalars().all()
        if servicios_existentes:
            print(f"Servicio ya tiene {len(servicios_existentes)} fila(s), no se siembra de nuevo.")
        else:
            session.add_all([Servicio(**s) for s in CATALOGO_SERVICIO])
            print(f"Catálogo Servicio sembrado ({len(CATALOGO_SERVICIO)} filas).")

        await session.commit()


async def main() -> None:
    db_url = os.environ.get("AZURE_DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "Falta la variable de entorno AZURE_DATABASE_URL "
            "(el secreto 'database-url' del Key Vault kv-techfix-2026)."
        )

    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        await crear_schemas(engine)
        await crear_tablas(engine)
        await sembrar_catalogo(engine)
    finally:
        await engine.dispose()

    print("\nListo — schema inicializado en la base nueva de techfix-infra.")


if __name__ == "__main__":
    asyncio.run(main())
