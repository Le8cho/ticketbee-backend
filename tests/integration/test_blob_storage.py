"""
Tests de integración para los endpoints de Blob Storage.
- POST /dispositivos/{id}/foto
- GET  /dispositivos/{id}/foto
- POST /tickets/{id}/adjuntos
- GET  /tickets/{id}/adjuntos
- GET  /adjuntos/{id}/url
- DELETE /adjuntos/{id}

Cubren validaciones (413, 422, 404) sin necesitar Azure real.
Los tests de upload exitoso requieren .env con AZURE_STORAGE_CONNECTION_STR configurado.

Ejecutar:
    uv run pytest tests/integration/test_blob_storage.py -v
"""
import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from app.utils.security import get_current_cliente, get_current_user_dev

CLIENTE_ID_TEST = uuid.UUID("00000000-0000-0000-0000-000000000099")
TECNICO_ID_TEST = uuid.UUID("00000000-0000-0000-0000-000000000001")

# UUIDs inexistentes para provocar 404
UUID_INEXISTENTE = str(uuid.uuid4())

IMAGEN_VALIDA = b"\xff\xd8\xff" + b"x" * 100   # cabecera JPEG mínima + relleno
IMAGEN_GRANDE = b"x" * (5 * 1024 * 1024 + 1)   # 5 MB + 1 byte → 413


def mock_cliente():
    return CLIENTE_ID_TEST


class MockUsuario:
    def __init__(self, rol: str):
        self.user_id = TECNICO_ID_TEST
        self.rol = rol


def mock_tecnico():
    return MockUsuario("tecnico")


app.dependency_overrides[get_current_cliente] = mock_cliente
app.dependency_overrides[get_current_user_dev] = mock_tecnico


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Foto de dispositivo ───────────────────────────────────────────────────────

class TestSubirFotoDispositivo:
    async def test_uuid_invalido_devuelve_422(self, client):
        files = {"foto": ("photo.jpg", IMAGEN_VALIDA, "image/jpeg")}
        response = await client.post("/api/v1/dispositivos/no-es-uuid/foto", files=files)
        assert response.status_code == 422

    async def test_archivo_demasiado_grande_devuelve_413(self, client):
        files = {"foto": ("grande.jpg", IMAGEN_GRANDE, "image/jpeg")}
        response = await client.post(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto", files=files)
        assert response.status_code == 413

    async def test_mime_invalido_devuelve_422(self, client):
        files = {"foto": ("video.mp4", b"fake content", "video/mp4")}
        response = await client.post(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto", files=files)
        assert response.status_code == 422

    async def test_pdf_no_permitido_como_foto_devuelve_422(self, client):
        files = {"foto": ("doc.pdf", b"%PDF-fake", "application/pdf")}
        response = await client.post(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto", files=files)
        assert response.status_code == 422

    async def test_dispositivo_inexistente_devuelve_404(self, client):
        files = {"foto": ("photo.jpg", IMAGEN_VALIDA, "image/jpeg")}
        response = await client.post(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto", files=files)
        assert response.status_code == 404

    async def test_sin_archivo_devuelve_422(self, client):
        response = await client.post(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto")
        assert response.status_code == 422


class TestObtenerFotoDispositivo:
    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/dispositivos/no-es-uuid/foto")
        assert response.status_code == 422

    async def test_dispositivo_inexistente_devuelve_404(self, client):
        response = await client.get(f"/api/v1/dispositivos/{UUID_INEXISTENTE}/foto")
        assert response.status_code == 404


# ── Adjuntos de ticket ────────────────────────────────────────────────────────

class TestSubirAdjunto:
    async def test_uuid_invalido_devuelve_422(self, client):
        files = {"archivo": ("doc.pdf", b"%PDF-fake", "application/pdf")}
        response = await client.post("/api/v1/tickets/no-es-uuid/adjuntos", files=files)
        assert response.status_code == 422

    async def test_archivo_demasiado_grande_devuelve_413(self, client):
        datos_grandes = b"x" * (10 * 1024 * 1024 + 1)
        files = {"archivo": ("grande.pdf", datos_grandes, "application/pdf")}
        response = await client.post(f"/api/v1/tickets/{UUID_INEXISTENTE}/adjuntos", files=files)
        assert response.status_code == 413

    async def test_mime_invalido_devuelve_422(self, client):
        files = {"archivo": ("video.mp4", b"fake content", "video/mp4")}
        response = await client.post(f"/api/v1/tickets/{UUID_INEXISTENTE}/adjuntos", files=files)
        assert response.status_code == 422

    async def test_ticket_inexistente_devuelve_404(self, client):
        files = {"archivo": ("doc.pdf", b"%PDF-fake", "application/pdf")}
        response = await client.post(f"/api/v1/tickets/{UUID_INEXISTENTE}/adjuntos", files=files)
        assert response.status_code == 404

    async def test_sin_archivo_devuelve_422(self, client):
        response = await client.post(f"/api/v1/tickets/{UUID_INEXISTENTE}/adjuntos")
        assert response.status_code == 422


class TestListarAdjuntos:
    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/tickets/no-es-uuid/adjuntos")
        assert response.status_code == 422

    async def test_ticket_inexistente_devuelve_lista_vacia(self, client):
        """Ticket inexistente → lista vacía, no 404 (no validamos existencia en listar)."""
        response = await client.get(f"/api/v1/tickets/{UUID_INEXISTENTE}/adjuntos")
        assert response.status_code == 200
        assert response.json()["data"] == []


class TestObtenerUrlAdjunto:
    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.get("/api/v1/adjuntos/no-es-uuid/url")
        assert response.status_code == 422

    async def test_adjunto_inexistente_devuelve_404(self, client):
        response = await client.get(f"/api/v1/adjuntos/{UUID_INEXISTENTE}/url")
        assert response.status_code == 404


class TestEliminarAdjunto:
    async def test_uuid_invalido_devuelve_422(self, client):
        response = await client.delete("/api/v1/adjuntos/no-es-uuid")
        assert response.status_code == 422

    async def test_adjunto_inexistente_devuelve_404(self, client):
        response = await client.delete(f"/api/v1/adjuntos/{UUID_INEXISTENTE}")
        assert response.status_code == 404
