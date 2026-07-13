"""
Ejecutar desde la raíz del proyecto:
    python scripts/check_db.py

Verifica que el DATABASE_URL del .env conecta correctamente a Supabase
y que las tablas del módulo de dispositivos existen y tienen datos.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database import engine


async def main():
    print("\n=== Verificación de conexión a Supabase ===\n")

    try:
        async with engine.connect() as conn:
            # 1. Conexión básica
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✓ Conexión exitosa")
            print(f"  PostgreSQL: {version[:50]}...\n")

            # 2. Schemas
            result = await conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('owner', 'clientes', 'pagos') ORDER BY schema_name"
            ))
            schemas = [r[0] for r in result.fetchall()]
            print(f"✓ Schemas encontrados: {schemas}\n")

            # 3. Tablas
            result = await conn.execute(text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema IN ('owner', 'clientes', 'pagos') ORDER BY table_schema, table_name"
            ))
            tablas = result.fetchall()
            print(f"✓ Tablas encontradas ({len(tablas)}):")
            for schema, tabla in tablas:
                print(f"  {schema}.{tabla}")
            print()

            # 4. Tipos de dispositivo
            result = await conn.execute(text(
                "SELECT tipo_dispositivo_id, nombre FROM owner.tipo_dispositivo "
                "WHERE activo = TRUE ORDER BY nombre"
            ))
            tipos = result.fetchall()
            print(f"✓ Tipos de dispositivo activos ({len(tipos)}):")
            for tid, nombre in tipos:
                print(f"  [{tid}] {nombre}")
            print()

    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nRevisá que DATABASE_URL en tu .env sea correcto.")
        print("Formato esperado:")
        print("  postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres")
        sys.exit(1)
    finally:
        await engine.dispose()

    print("=== Todo OK. La conexión funciona correctamente. ===\n")


asyncio.run(main())
