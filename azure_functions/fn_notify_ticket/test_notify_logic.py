"""
Prueba la logica de fn-notify-ticket sin necesitar el backend ni ACS reales.
Mockeamos la consulta del cliente/tecnico y el envio de email.

Uso: .venv/Scripts/python.exe test_notify_logic.py
"""

import os
os.environ.setdefault("BACKEND_URL", "http://backend-de-prueba")
os.environ.setdefault("SUPABASE_URL", "http://supabase-de-prueba")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-de-prueba")
os.environ.setdefault("TECNICO_SERVICE_EMAIL", "tecnico@prueba.com")
os.environ.setdefault("TECNICO_SERVICE_PASSWORD", "prueba123")

from unittest.mock import patch, MagicMock

from notify_logic import procesar_evento

_mock_auth = patch("notify_logic.auth_headers", return_value={"Authorization": "Bearer jwt-de-prueba"})
_mock_cliente_get = patch(
    "notify_logic.requests.get",
    return_value=MagicMock(status_code=200, json=lambda: {
        "data": {"email": "cliente@prueba.com", "nombre": "Cliente De Prueba"}
    }),
)


def test_ticket_creado_notifica_al_cliente():
    payload = {"evento": "ticket.creado", "ticket_id": "t1", "cliente_id": "c1", "servicio_id": "s1"}
    with _mock_auth, _mock_cliente_get, patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado == {"processed": True, "evento": "ticket.creado"}
    kwargs = mock_email.call_args.kwargs
    assert "recibido" in kwargs["asunto"].lower()
    assert "t1" in kwargs["asunto"]
    print("[OK] ticket.creado notifica al cliente con la plantilla nueva\n")


def test_ticket_aceptado_incluye_precio_final_y_yape():
    payload = {"evento": "ticket.aceptado", "ticket_id": "t1", "cliente_id": "c1", "precio_final": "150.00"}
    with _mock_auth, _mock_cliente_get, patch("notify_logic.enviar_email") as mock_email:
        procesar_evento(payload)

    cuerpo = mock_email.call_args.kwargs["cuerpo"]
    assert "150.00" in cuerpo
    assert "Yape" in cuerpo
    print("[OK] ticket.aceptado incluye el monto y la instrucción de pago por Yape\n")


def test_ticket_rechazado_incluye_motivo():
    payload = {
        "evento": "ticket.rechazado", "ticket_id": "t1", "cliente_id": "c1",
        "motivo_rechazo": "Repuesto no disponible",
    }
    with _mock_auth, _mock_cliente_get, patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    cuerpo = mock_email.call_args.kwargs["cuerpo"]
    assert "Repuesto no disponible" in cuerpo
    assert resultado["processed"] is True
    print("[OK] ticket.rechazado incluye el motivo real en el cuerpo\n")


def test_ticket_entrega_confirmada_notifica_al_cliente():
    payload = {"evento": "ticket.entrega_confirmada", "ticket_id": "t1", "cliente_id": "c1"}
    with _mock_auth, _mock_cliente_get, patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado["processed"] is True
    mock_email.assert_called_once()
    print("[OK] ticket.entrega_confirmada notifica al cliente\n")


def test_ticket_reabierto_busca_al_tecnico_especifico():
    payload = {"evento": "ticket.reabierto", "ticket_id": "t1", "cliente_id": "c1", "tecnico_id": "tec1"}
    mock_get_tecnico = MagicMock(
        status_code=200,
        json=lambda: {"data": {"email": "tecnico_real@prueba.com", "nombre": "Tecnico Real"}},
    )
    with _mock_auth, patch("notify_logic.requests.get", return_value=mock_get_tecnico) as get_mock, \
         patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado["processed"] is True
    assert "/tecnicos/tec1" in get_mock.call_args.args[0]
    kwargs = mock_email.call_args.kwargs
    assert kwargs["destinatario"] == "tecnico_real@prueba.com"
    assert kwargs["nombre_destinatario"] == "Tecnico Real"
    print("[OK] ticket.reabierto busca y notifica al tecnico especifico asignado\n")


def test_ticket_reabierto_sin_tecnico_id_no_falla():
    payload = {"evento": "ticket.reabierto", "ticket_id": "t1", "cliente_id": "c1"}
    with patch("notify_logic.requests.get") as get_mock, patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado["processed"] is True
    get_mock.assert_not_called()
    mock_email.assert_not_called()
    print("[OK] ticket.reabierto sin tecnico_id no rompe, solo no notifica\n")


def test_ticket_finalizado_no_tiene_handler():
    payload = {"evento": "ticket.finalizado", "ticket_id": "t1", "cliente_id": "c1"}
    with patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado == {"processed": False, "reason": "evento 'ticket.finalizado' sin handler"}
    mock_email.assert_not_called()
    print("[OK] ticket.finalizado se ignora a proposito (fn-warranty ya notifica)\n")


def test_evento_desconocido_se_ignora():
    payload = {"evento": "evento.inventado", "ticket_id": "t1"}
    with patch("notify_logic.enviar_email") as mock_email:
        resultado = procesar_evento(payload)

    assert resultado["processed"] is False
    mock_email.assert_not_called()
    print("[OK] Evento desconocido se ignora sin romper nada\n")


if __name__ == "__main__":
    test_ticket_creado_notifica_al_cliente()
    test_ticket_aceptado_incluye_precio_final_y_yape()
    test_ticket_rechazado_incluye_motivo()
    test_ticket_entrega_confirmada_notifica_al_cliente()
    test_ticket_reabierto_busca_al_tecnico_especifico()
    test_ticket_reabierto_sin_tecnico_id_no_falla()
    test_ticket_finalizado_no_tiene_handler()
    test_evento_desconocido_se_ignora()
    print("Listo.")
