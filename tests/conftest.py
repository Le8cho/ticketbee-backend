"""
Configuración global de tests.

NullPool: evita que asyncpg reutilice conexiones entre tests.
Sin esto, el pool queda atado al event loop del primer test
y los siguientes fallan con "another operation is in progress".
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

import app.database as db_module
from app.config import settings


@pytest.fixture(scope="session", autouse=True)
def setup_test_engine():
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    db_module.engine = test_engine
    db_module.AsyncSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)
    yield
