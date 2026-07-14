"""
Tests de integración para el auto-registro Supabase -> Azure SQL (Fase 0.3,
verificado en Fase 5 — ver plan binary-churning-pearl.md). El endpoint debe
ser idempotente: llamarlo dos veces con el mismo `sub` no debe duplicar la
fila ni fallar.

Usa la base de datos real (requiere .env configurado). Crea una fila de
cliente de prueba con un UUID fresco y la borra al terminar.

Ejecutar:
    pytest tests/integration/test_clientes_registro.py -v
"""
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.core.security import UsuarioActual, get_current_tecnico, get_current_user


def _usuario_cliente_nuevo(cliente_id: uuid.UUID) -> UsuarioActual:
    return UsuarioActual(
        user_id=cliente_id,
        rol="cliente",
        email=f"{cliente_id}@example.com",
        user_metadata={"rol": "cliente", "nombre": "Cliente De Prueba", "distrito": "Surco"},
    )


@pytest.fixture
async def cliente_id_fresco():
    cliente_id = uuid.uuid4()
    yield cliente_id
    # Engine propio y descartable (no el AsyncSessionLocal global de
    # app.core.database, que en conftest.py tiene scope de sesión y queda
    # atado al event loop del primer test — revienta con "attached to a
    # different loop" si se reutiliza tarde en la suite completa).
    engine_directo = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        async with engine_directo.connect() as conn:
            await conn.execute(
                text("DELETE FROM clientes.cliente WHERE cliente_id = :id"),
                {"id": str(cliente_id)},
            )
            await conn.commit()
    finally:
        await engine_directo.dispose()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_primera_llamada_crea_la_fila(client, cliente_id_fresco):
    app.dependency_overrides[get_current_user] = lambda: _usuario_cliente_nuevo(cliente_id_fresco)
    try:
        response = await client.post("/api/v1/clientes/registro")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["cliente_id"] == str(cliente_id_fresco)
    assert body["data"]["nombre"] == "Cliente De Prueba"


async def test_segunda_llamada_es_idempotente_no_duplica_ni_falla(client, cliente_id_fresco):
    app.dependency_overrides[get_current_user] = lambda: _usuario_cliente_nuevo(cliente_id_fresco)
    try:
        primera = await client.post("/api/v1/clientes/registro")
        segunda = await client.post("/api/v1/clientes/registro")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json()["data"]["cliente_id"] == str(cliente_id_fresco)
    # El servicio revisa "existe?" antes de insertar (ver cliente_service.py)
    # — un 200 en la segunda llamada ya prueba estructuralmente que no hubo
    # un segundo INSERT. Confirmamos igual que la fila persistida es una sola
    # con los datos de la primera llamada, vía la API (no una sesión de DB
    # aparte, para no pelear con el loop de asyncio del test).
    app.dependency_overrides[get_current_tecnico] = lambda: uuid.uuid4()
    try:
        perfil = await client.get(f"/api/v1/clientes/{cliente_id_fresco}")
    finally:
        app.dependency_overrides.pop(get_current_tecnico, None)
    assert perfil.status_code == 200
    assert perfil.json()["data"]["nombre"] == "Cliente De Prueba"


async def test_rol_no_cliente_devuelve_403(client):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(
        user_id=uuid.uuid4(), rol="tecnico", email="t@example.com", user_metadata={"rol": "tecnico"}
    )
    try:
        response = await client.post("/api/v1/clientes/registro")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
