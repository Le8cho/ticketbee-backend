"""
Tests de integración para el módulo de Clientes (SD-17).
Usan la base de datos real de Supabase (requiere .env configurado).

Ejecutar:
    pytest tests/integration/test_clientes.py -v
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.utils.security import get_current_tecnico

TECNICO_ID_TEST = uuid.UUID("00000000-0000-0000-0000-000000000001")
CLIENTE_ID_INEXISTENTE = uuid.UUID("00000000-0000-0000-0000-000000000000")


def mock_tecnico_auth():
    """Reemplaza el JWT real por un UUID fijo para los tests."""
    return TECNICO_ID_TEST


app.dependency_overrides[get_current_tecnico] = mock_tecnico_auth


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── GET /api/v1/clientes ──────────────────────────────────────────────────────

class TestListarClientes:

    async def test_devuelve_200(self, client):
        response = await client.get("/api/v1/clientes")
        assert response.status_code == 200

    async def test_estructura_respuesta(self, client):
        response = await client.get("/api/v1/clientes")
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["data"], list)

    async def test_items_tienen_campos_requeridos(self, client):
        response = await client.get("/api/v1/clientes")
        data = response.json()["data"]
        if not data:
            pytest.skip("No hay clientes en la BD de prueba")
        item = data[0]
        for campo in ("cliente_id", "nombre", "email", "distrito", "tickets_activos", "creado_en"):
            assert campo in item, f"Campo '{campo}' falta en la respuesta"

    async def test_tickets_activos_es_entero_no_negativo(self, client):
        response = await client.get("/api/v1/clientes")
        data = response.json()["data"]
        for item in data:
            assert isinstance(item["tickets_activos"], int)
            assert item["tickets_activos"] >= 0

    async def test_filtro_distrito(self, client):
        response = await client.get("/api/v1/clientes", params={"distrito": "Miraflores"})
        assert response.status_code == 200
        data = response.json()["data"]
        for item in data:
            assert item["distrito"] == "Miraflores"

    async def test_filtro_estado_ticket_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/clientes", params={"estado_ticket": "ESTADO_QUE_NO_EXISTE"})
        assert response.status_code == 422

    async def test_filtro_fecha_desde_formato_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/clientes", params={"fecha_desde": "no-es-una-fecha"})
        assert response.status_code == 422

    async def test_sin_token_devuelve_403(self):
        app.dependency_overrides.pop(get_current_tecnico, None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/clientes")
        app.dependency_overrides[get_current_tecnico] = mock_tecnico_auth
        assert response.status_code in (401, 403)


# ── GET /api/v1/clientes/{cliente_id} ─────────────────────────────────────────

class TestPerfilCliente:

    async def test_cliente_inexistente_devuelve_404(self, client):
        response = await client.get(f"/api/v1/clientes/{CLIENTE_ID_INEXISTENTE}")
        assert response.status_code == 404

    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/clientes/no-es-un-uuid")
        assert response.status_code == 422

    async def test_cliente_existente_devuelve_200(self, client):
        listado = await client.get("/api/v1/clientes")
        clientes = listado.json()["data"]
        if not clientes:
            pytest.skip("No hay clientes en la BD de prueba")
        cliente_id = clientes[0]["cliente_id"]
        response = await client.get(f"/api/v1/clientes/{cliente_id}")
        assert response.status_code == 200

    async def test_perfil_tiene_campos_requeridos(self, client):
        listado = await client.get("/api/v1/clientes")
        clientes = listado.json()["data"]
        if not clientes:
            pytest.skip("No hay clientes en la BD de prueba")
        cliente_id = clientes[0]["cliente_id"]
        response = await client.get(f"/api/v1/clientes/{cliente_id}")
        data = response.json()["data"]
        for campo in ("cliente_id", "nombre", "email", "distrito", "email_verificado", "dispositivos"):
            assert campo in data, f"Campo '{campo}' falta en el perfil"

    async def test_dispositivos_es_lista(self, client):
        listado = await client.get("/api/v1/clientes")
        clientes = listado.json()["data"]
        if not clientes:
            pytest.skip("No hay clientes en la BD de prueba")
        cliente_id = clientes[0]["cliente_id"]
        response = await client.get(f"/api/v1/clientes/{cliente_id}")
        assert isinstance(response.json()["data"]["dispositivos"], list)

    async def test_sin_token_devuelve_403(self):
        app.dependency_overrides.pop(get_current_tecnico, None)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/clientes/{CLIENTE_ID_INEXISTENTE}")
        app.dependency_overrides[get_current_tecnico] = mock_tecnico_auth
        assert response.status_code in (401, 403)
