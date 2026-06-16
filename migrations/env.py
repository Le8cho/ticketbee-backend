import asyncio
import os
import sys
from logging.config import fileConfig
# Al inicio del archivo, agrega:
from app.database import Base
from app.models import dispositivo, cliente, pago, ticket_model  # importa todos los modelos

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Agrega raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importar Base y TODOS los modelos para que Alembic los detecte
from app.database import Base          # noqa: E402
from app.config import settings        # noqa: E402
from app.models import (               # noqa: E402, F401
    cliente, dispositivo, pago, ticket, tipo_dispositivo
)
from app.models import tecnico         # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Inyectar DATABASE_URL desde .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
