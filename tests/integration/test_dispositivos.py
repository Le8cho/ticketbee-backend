"""
Tests de integración para el módulo de Dispositivos.
Usan la base de datos real de Supabase (requiere .env configurado).

Ejecutar:
    pytest tests/integration/test_dispositivos.py -v
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import get_current_cliente, get_current_user, UsuarioActual

CLIENTE_ID_TEST = uuid.UUID("00000000-0000-0000-0000-000000000099")


def mock_auth():
    """Reemplaza el JWT real por un UUID fijo para los tests."""
    return CLIENTE_ID_TEST


def mock_auth_usuario():
    """Idem, pero para endpoints que dependen de get_current_user (necesitan el rol)."""
    return UsuarioActual(user_id=CLIENTE_ID_TEST, rol="cliente")


@pytest.fixture(scope="module", autouse=True)
def _override_auth():
    """Scoped a este módulo: evita pisar los overrides de otros archivos de test
    que comparten el mismo `app.dependency_overrides` (get_current_user_dev es
    el mismo objeto que get_current_user)."""
    app.dependency_overrides[get_current_cliente] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth_usuario
    yield
    app.dependency_overrides.pop(get_current_cliente, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Tipos de dispositivo (endpoint público) ───────────────────────────────────

class TestListarTipos:
    async def test_devuelve_200(self, client):
        response = await client.get("/api/v1/dispositivos/tipos")
        assert response.status_code == 200

    async def test_estructura_respuesta(self, client):
        response = await client.get("/api/v1/dispositivos/tipos")
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["data"], list)

    async def test_tiene_tipos_cargados(self, client):
        """La DB de Supabase tiene 11 tipos cargados por el SQL inicial."""
        response = await client.get("/api/v1/dispositivos/tipos")
        data = response.json()["data"]
        assert len(data) >= 1

    async def test_estructura_tipo(self, client):
        response = await client.get("/api/v1/dispositivos/tipos")
        tipo = response.json()["data"][0]
        assert "tipo_dispositivo_id" in tipo
        assert "nombre" in tipo


# ── Listar dispositivos ───────────────────────────────────────────────────────

class TestListarDispositivos:
    async def test_devuelve_200(self, client):
        response = await client.get("/api/v1/dispositivos")
        assert response.status_code == 200

    async def test_estructura_respuesta(self, client):
        response = await client.get("/api/v1/dispositivos")
        body = response.json()
        assert body["ok"] is True
        assert isinstance(body["data"], list)

    async def test_cliente_nuevo_no_tiene_dispositivos(self, client):
        """El CLIENTE_ID_TEST no existe en DB → lista vacía, no error."""
        response = await client.get("/api/v1/dispositivos")
        assert response.json()["data"] == []


# ── Registrar dispositivo ─────────────────────────────────────────────────────

class TestRegistrarDispositivo:
    async def test_tipo_invalido_devuelve_400(self, client):
        payload = {
            "tipo_dispositivo_id": 9999,
            "marca": "Samsung",
            "modelo": "Galaxy S24",
        }
        response = await client.post("/api/v1/dispositivos", json=payload)
        assert response.status_code == 400

    async def test_campos_requeridos_faltantes_devuelve_422(self, client):
        response = await client.post("/api/v1/dispositivos", json={"marca": "Samsung"})
        assert response.status_code == 422

    async def test_marca_vacia_devuelve_422(self, client):
        payload = {
            "tipo_dispositivo_id": 1,
            "marca": "",
            "modelo": "Galaxy S24",
        }
        response = await client.post("/api/v1/dispositivos", json=payload)
        assert response.status_code == 422


# ── Actualizar dispositivo ────────────────────────────────────────────────────

class TestActualizarDispositivo:
    async def test_dispositivo_inexistente_devuelve_404(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.patch(f"/api/v1/dispositivos/{fake_id}", json={"marca": "Apple"})
        assert response.status_code == 404

    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.patch("/api/v1/dispositivos/no-es-uuid", json={"marca": "Apple"})
        assert response.status_code == 422


# ── Desactivar dispositivo ────────────────────────────────────────────────────

class TestDesactivarDispositivo:
    async def test_dispositivo_inexistente_devuelve_404(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/dispositivos/{fake_id}")
        assert response.status_code == 404
