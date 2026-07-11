"""
Prueba la logica de fn-warranty sin necesitar el backend real corriendo
(el endpoint POST /tickets/{id}/garantia todavia no existe del lado de Persona 2).
Mockeamos la llamada HTTP para validar SOLO la logica de calculo y el payload enviado.

Uso: .venv/Scripts/python.exe test_garantia_logic.py
"""

import os
os.environ.setdefault("BACKEND_URL", "http://backend-de-prueba")
os.environ.setdefault("SUPABASE_URL", "http://supabase-de-prueba")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-de-prueba")
os.environ.setdefault("TECNICO_SERVICE_EMAIL", "tecnico@prueba.com")
os.environ.setdefault("TECNICO_SERVICE_PASSWORD", "prueba123")

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from garantia_logic import procesar_evento

TICKET_ID_DE_PRUEBA = "DDDD0001-0000-0000-0000-000000000000"


def test_pago_exitoso_llama_al_backend():
    fecha_finalizacion = datetime(2026, 6, 22, tzinfo=timezone.utc)
    evento = {
        "evento": "ticket.finalizado",
        "ticket_id": TICKET_ID_DE_PRUEBA,
        "cliente_id": "00000000-0000-0000-0000-000000000001",
        "fecha_finalizacion": fecha_finalizacion.isoformat(),
    }

    mock_response = MagicMock(
        status_code=201,
        json=lambda: {"data": {
            "ticket_id": TICKET_ID_DE_PRUEBA,
            "cliente_email": "cliente@prueba.com",
            "cliente_nombre": "Cliente De Prueba",
        }},
    )
    with patch("garantia_logic.requests.post", return_value=mock_response) as mock_post, \
         patch("garantia_logic.auth_headers", return_value={"Authorization": "Bearer jwt-de-prueba"}), \
         patch("garantia_logic.enviar_email_garantia_activada") as mock_email:
        resultado = procesar_evento(evento)

    print("Resultado:", resultado)
    assert resultado["processed"] is True
    assert resultado["fecha_vencimiento"] == "2026-06-29T00:00:00+00:00"  # +7 dias

    kwargs = mock_post.call_args[1]
    print("URL llamada:", mock_post.call_args)
    assert f"/tickets/{TICKET_ID_DE_PRUEBA}/garantia" in mock_post.call_args.args[0]
    assert kwargs["json"]["fecha_inicio"] == "2026-06-22T00:00:00+00:00"
    assert kwargs["json"]["fecha_vencimiento"] == "2026-06-29T00:00:00+00:00"
    assert kwargs["headers"]["Authorization"] == "Bearer jwt-de-prueba"

    mock_email.assert_called_once()
    email_kwargs = mock_email.call_args.kwargs
    assert email_kwargs["cliente_email"] == "cliente@prueba.com"
    assert email_kwargs["cliente_nombre"] == "Cliente De Prueba"
    print("[OK] Llama al backend con la fecha correcta (+7 dias), el JWT, y manda el email\n")


def test_evento_ignorado_no_llama_al_backend():
    evento = {
        "evento": "ticket.creado",
        "ticket_id": TICKET_ID_DE_PRUEBA,
        "fecha_finalizacion": datetime.now(timezone.utc).isoformat(),
    }
    with patch("garantia_logic.requests.post") as mock_post:
        resultado = procesar_evento(evento)

    assert resultado["processed"] is False
    mock_post.assert_not_called()
    print("[OK] Evento distinto a ticket.finalizado se ignora, sin llamar al backend\n")


def test_payload_incompleto_lanza_error():
    evento = {"evento": "ticket.finalizado", "ticket_id": TICKET_ID_DE_PRUEBA}
    try:
        procesar_evento(evento)
        print("[FALLO] Deberia haber lanzado ValueError")
    except ValueError as e:
        print(f"[OK] Lanza ValueError correctamente: {e}\n")


def test_backend_rechaza_la_solicitud():
    evento = {
        "evento": "ticket.finalizado",
        "ticket_id": TICKET_ID_DE_PRUEBA,
        "fecha_finalizacion": datetime.now(timezone.utc).isoformat(),
    }
    mock_response = MagicMock(status_code=500, text="error interno")
    with patch("garantia_logic.requests.post", return_value=mock_response), \
         patch("garantia_logic.auth_headers", return_value={"Authorization": "Bearer jwt-de-prueba"}):
        try:
            procesar_evento(evento)
            print("[FALLO] Deberia haber lanzado RuntimeError")
        except RuntimeError as e:
            print(f"[OK] Lanza RuntimeError cuando el backend rechaza: {e}\n")


if __name__ == "__main__":
    test_pago_exitoso_llama_al_backend()
    test_evento_ignorado_no_llama_al_backend()
    test_payload_incompleto_lanza_error()
    test_backend_rechaza_la_solicitud()
    print("Listo.")
