"""
Tests de integración para la configuración de CORS (Fase 5 — ver plan
binary-churning-pearl.md). Confirma que las respuestas incluyen los headers
de CORS para el origen permitido, tanto en un preflight OPTIONS como en un
GET real.

Ejecutar:
    pytest tests/integration/test_cors.py -v
"""
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings

ORIGEN_PERMITIDO = settings.cors_origins_list[0]


async def test_preflight_options_incluye_headers_cors():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.options(
            "/api/v1/catalogo/servicios",
            headers={
                "Origin": ORIGEN_PERMITIDO,
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ORIGEN_PERMITIDO


async def test_get_real_incluye_access_control_allow_origin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health", headers={"Origin": ORIGEN_PERMITIDO})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ORIGEN_PERMITIDO


async def test_origen_no_permitido_no_recibe_allow_origin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health", headers={"Origin": "https://sitio-no-autorizado.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
