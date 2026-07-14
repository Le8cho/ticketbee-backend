"""
Test de integración del ciclo de vida completo de un ticket (Fase 5 — ver
plan binary-churning-pearl.md):

    EN_REVISION -> EN_ESPERA_PAGO -> EN_PROGRESO -> FINALIZADO -> ARCHIVADO

Cubre también los guards 409 en transiciones inválidas ya existentes en
ticket_service.py. Usa la base de datos real (requiere .env configurado).

El paso EN_ESPERA_PAGO -> EN_PROGRESO no tiene endpoint HTTP por diseño (solo
debe cambiar por el webhook real de Mercado Pago, ver payments.py) — se
simula con un UPDATE directo, igual que documenta END-TO-END.md paso 8. Ese
UPDATE usa un engine propio y descartable (no el `AsyncSessionLocal` global de
`app.core.database`, que en `conftest.py` tiene scope de sesión): reutilizar
el engine global funciona en tests aislados pero revienta con "attached to a
different loop" cuando corre después de muchos otros tests, porque queda
atado al event loop del primer test de toda la sesión de pytest.

Ejecutar:
    pytest tests/integration/test_ticket_lifecycle.py -v
"""
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings
from app.core.security import (
    UsuarioActual,
    get_current_cliente,
    get_current_tecnico,
    get_current_user,
)

TECNICO_ID = uuid.UUID("2ed61426-99e6-4a6f-9a8c-0b8c0edc013d")  # Tecnico Debug, fila real
SERVICIO_ID = uuid.UUID("86692dc1-9dfd-41be-be09-1343edfdccfc")  # "Reparación Dummy", S/45


def _usuario_cliente(cliente_id: uuid.UUID) -> UsuarioActual:
    return UsuarioActual(
        user_id=cliente_id,
        rol="cliente",
        email=f"{cliente_id}@example.com",
        user_metadata={"rol": "cliente", "nombre": "Ciclo De Prueba", "distrito": "Surco"},
    )


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_ciclo_completo_de_estados_y_guards_409(client):
    cliente_id = uuid.uuid4()

    # 1. Provisionar cliente + dispositivo (vía API real, no DB cruda)
    app.dependency_overrides[get_current_user] = lambda: _usuario_cliente(cliente_id)
    registro = await client.post("/api/v1/clientes/registro")
    app.dependency_overrides.pop(get_current_user, None)
    assert registro.status_code == 201

    app.dependency_overrides[get_current_cliente] = lambda: cliente_id
    tipos = await client.get("/api/v1/dispositivos/tipos")
    tipo_dispositivo_id = tipos.json()["data"][0]["tipo_dispositivo_id"]
    dispositivo_resp = await client.post(
        "/api/v1/dispositivos",
        json={"tipo_dispositivo_id": tipo_dispositivo_id, "marca": "TestBrand", "modelo": "CicloVida"},
    )
    assert dispositivo_resp.status_code == 201
    dispositivo_id = dispositivo_resp.json()["data"]["dispositivo_id"]

    # 2. Crear ticket -> EN_REVISION
    ticket_resp = await client.post(
        "/api/v1/tickets",
        json={"dispositivo_id": dispositivo_id, "servicio_id": str(SERVICIO_ID)},
    )
    app.dependency_overrides.pop(get_current_cliente, None)
    assert ticket_resp.status_code == 201
    ticket = ticket_resp.json()["data"]
    ticket_id = ticket["ticket_id"]
    assert ticket["estado"] == "EN_REVISION"

    try:
        # Guard: el cliente no puede confirmar recepción de un ticket en EN_REVISION
        app.dependency_overrides[get_current_cliente] = lambda: cliente_id
        guard_recepcion_temprana = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-recepcion")
        app.dependency_overrides.pop(get_current_cliente, None)
        assert guard_recepcion_temprana.status_code == 409

        # 3. Técnico acepta -> EN_ESPERA_PAGO
        app.dependency_overrides[get_current_tecnico] = lambda: TECNICO_ID
        aceptar = await client.patch(
            f"/api/v1/tickets/{ticket_id}/aceptar", json={"precio_final": 45.00}
        )
        assert aceptar.status_code == 200
        assert aceptar.json()["data"]["estado"] == "EN_ESPERA_PAGO"

        # Guard: no se puede aceptar dos veces
        aceptar_de_nuevo = await client.patch(
            f"/api/v1/tickets/{ticket_id}/aceptar", json={"precio_final": 45.00}
        )
        assert aceptar_de_nuevo.status_code == 409

        # Guard: no se puede rechazar un ticket que ya salió de EN_REVISION
        rechazar_tarde = await client.patch(
            f"/api/v1/tickets/{ticket_id}/rechazar",
            json={"motivo_rechazo": "ya fue aceptado antes"},
        )
        assert rechazar_tarde.status_code == 409

        # Guard: no se puede confirmar entrega antes de que se pague
        entrega_temprana = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-entrega")
        assert entrega_temprana.status_code == 409
        app.dependency_overrides.pop(get_current_tecnico, None)

        # 4. Simular confirmación de pago -> EN_PROGRESO (sin endpoint HTTP
        # por diseño; único UPDATE crudo de todo el test, ver END-TO-END.md).
        # Engine propio y descartable, ver docstring del módulo.
        engine_directo = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        try:
            async with engine_directo.connect() as conn:
                await conn.execute(
                    text("UPDATE clientes.ticket SET estado = 'EN_PROGRESO' WHERE ticket_id = :id"),
                    {"id": str(ticket_id)},
                )
                await conn.commit()
        finally:
            await engine_directo.dispose()

        # 5. Técnico confirma entrega
        app.dependency_overrides[get_current_tecnico] = lambda: TECNICO_ID
        entrega = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-entrega")
        assert entrega.status_code == 200
        assert entrega.json()["data"]["confirmado_tecnico"] is True
        assert entrega.json()["data"]["estado"] == "EN_PROGRESO"

        # Guard: el técnico no puede confirmar entrega dos veces
        entrega_de_nuevo = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-entrega")
        assert entrega_de_nuevo.status_code == 409
        app.dependency_overrides.pop(get_current_tecnico, None)

        # 6. Cliente confirma recepción -> FINALIZADO
        app.dependency_overrides[get_current_cliente] = lambda: cliente_id
        recepcion = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-recepcion")
        assert recepcion.status_code == 200
        assert recepcion.json()["data"]["estado"] == "FINALIZADO"

        # Guard: el cliente no puede confirmar recepción dos veces
        recepcion_de_nuevo = await client.patch(f"/api/v1/tickets/{ticket_id}/confirmar-recepcion")
        assert recepcion_de_nuevo.status_code == 409
        app.dependency_overrides.pop(get_current_cliente, None)

        # 7. Técnico archiva -> ARCHIVADO
        app.dependency_overrides[get_current_tecnico] = lambda: TECNICO_ID
        archivar = await client.patch(f"/api/v1/tickets/{ticket_id}/archivar")
        assert archivar.status_code == 200

        # Guard: no se puede archivar dos veces
        archivar_de_nuevo = await client.patch(f"/api/v1/tickets/{ticket_id}/archivar")
        assert archivar_de_nuevo.status_code == 409
        app.dependency_overrides.pop(get_current_tecnico, None)

        # Verificación final del estado vía GET (rol técnico)
        app.dependency_overrides[get_current_user] = lambda: UsuarioActual(
            user_id=TECNICO_ID, rol="tecnico", email="tec@example.com", user_metadata={}
        )
        final = await client.get(f"/api/v1/tickets/{ticket_id}")
        app.dependency_overrides.pop(get_current_user, None)
        assert final.json()["data"]["estado"] == "ARCHIVADO"
    finally:
        app.dependency_overrides.pop(get_current_cliente, None)
        app.dependency_overrides.pop(get_current_tecnico, None)
        app.dependency_overrides.pop(get_current_user, None)
        # Cleanup del dispositivo vía API (soft-delete). El ticket queda
        # ARCHIVADO a propósito (no hay ni debe haber endpoint para borrar
        # tickets) y la fila de cliente de prueba queda huérfana — igual que
        # el resto de datos de prueba generados manualmente en este proyecto.
        app.dependency_overrides[get_current_cliente] = lambda: cliente_id
        await client.delete(f"/api/v1/dispositivos/{dispositivo_id}")
        app.dependency_overrides.pop(get_current_cliente, None)
