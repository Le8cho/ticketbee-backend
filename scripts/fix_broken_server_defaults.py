"""
Repara los DEFAULT CONSTRAINT rotos en la base NUEVA de techfix-infra (Azure SQL).

Bug: 4 columnas usaban server_default="GETUTCDATE()" / "SYSDATETIMEOFFSET()" como
string Python plano en el modelo de SQLAlchemy, en vez de sqlalchemy.text(...).
SQLAlchemy trata un string plano como literal citado en el DDL, así que el
CREATE TABLE original (scripts/init_azure_infra_schema.py, Paso 4) dejó el
default literalmente como el string 'GETUTCDATE()' en vez de una llamada a la
función — cualquier INSERT que dependa de ese default revienta con:
    pyodbc.DataError 22007: Conversion failed when converting date and/or
    time from character string.

Ya fijado en los modelos (app/models/cliente.py, tecnico.py, ticket.py,
garantia.py) para que un create_all futuro salga bien — este script solo
repara las 4 columnas que ya existen mal en la base real.

No toca filas existentes, solo reemplaza el DEFAULT CONSTRAINT de la columna.

Uso:
    AZURE_DATABASE_URL="$(az keyvault secret show --vault-name kv-techfix-2026 \
        --name database-url --query value -o tsv)" \
        uv run python scripts/fix_broken_server_defaults.py
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# (schema, tabla, columna, expresion_sql_correcta)
COLUMNAS_ROTAS = [
    ("clientes", "cliente", "creado_en", "GETUTCDATE()"),
    ("owner", "tecnico", "creado_en", "GETUTCDATE()"),
    ("clientes", "ticket", "actualizado_en", "SYSDATETIMEOFFSET()"),
    ("clientes", "garantia", "creado_en", "SYSDATETIMEOFFSET()"),
]


async def reparar_columna(conn, schema: str, tabla: str, columna: str, expresion: str) -> None:
    result = await conn.execute(
        text(
            "SELECT dc.name FROM sys.default_constraints dc "
            "JOIN sys.columns c ON dc.parent_object_id = c.object_id "
            "AND dc.parent_column_id = c.column_id "
            "WHERE dc.parent_object_id = OBJECT_ID(:tabla) AND c.name = :columna"
        ),
        {"tabla": f"{schema}.{tabla}", "columna": columna},
    )
    nombre_constraint = result.scalar_one_or_none()

    if nombre_constraint:
        await conn.execute(text(f"ALTER TABLE {schema}.{tabla} DROP CONSTRAINT [{nombre_constraint}]"))
        print(f"  {schema}.{tabla}.{columna}: constraint roto '{nombre_constraint}' eliminado.")
    else:
        print(f"  {schema}.{tabla}.{columna}: no tenia default constraint (nada que eliminar).")

    await conn.execute(text(f"ALTER TABLE {schema}.{tabla} ADD DEFAULT ({expresion}) FOR {columna}"))
    print(f"  {schema}.{tabla}.{columna}: nuevo default '{expresion}' aplicado.")


async def main() -> None:
    db_url = os.environ.get("AZURE_DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "Falta la variable de entorno AZURE_DATABASE_URL "
            "(el secreto 'database-url' del Key Vault kv-techfix-2026)."
        )

    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            for schema, tabla, columna, expresion in COLUMNAS_ROTAS:
                await reparar_columna(conn, schema, tabla, columna, expresion)
    finally:
        await engine.dispose()

    print("\nListo — los 4 default constraints quedaron reparados.")


if __name__ == "__main__":
    asyncio.run(main())
