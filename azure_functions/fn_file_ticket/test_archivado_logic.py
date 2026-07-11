"""
Prueba la logica de fn-file-ticket sin necesitar el backend real corriendo
(GET /tickets?garantia_vencida=true todavia no existe del lado de Persona 2).
Mockeamos las llamadas HTTP para validar SOLO la orquestacion.

Uso: .venv/Scripts/python.exe test_archivado_logic.py
"""

import os
os.environ.setdefault("BACKEND_URL", "http://backend-de-prueba")
os.environ.setdefault("SUPABASE_URL", "http://supabase-de-prueba")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-de-prueba")
os.environ.setdefault("TECNICO_SERVICE_EMAIL", "tecnico@prueba.com")
os.environ.setdefault("TECNICO_SERVICE_PASSWORD", "prueba123")

from unittest.mock import patch, MagicMock

from archivado_logic import archivar_tickets_vencidos

_mock_auth = patch("archivado_logic.auth_headers", return_value={"Authorization": "Bearer jwt-de-prueba"})
_mock_email = patch("archivado_logic.enviar_email_garantia_concluida")


def test_archiva_todos_los_tickets_vencidos():
    tickets_vencidos = [
        {"ticket_id": "dddd0004-0000-0000-0000-000000000000"},
        {"ticket_id": "dddd0008-0000-0000-0000-000000000000"},
    ]
    mock_get = MagicMock(status_code=200, json=lambda: {"data": tickets_vencidos})
    mock_patch = MagicMock(status_code=200, json=lambda: {"data": {"cliente_email": "c@prueba.com", "cliente_nombre": "Cliente"}})

    with _mock_auth, _mock_email as mock_email, \
         patch("archivado_logic.requests.get", return_value=mock_get) as get_mock, \
         patch("archivado_logic.requests.patch", return_value=mock_patch) as patch_mock:
        resultado = archivar_tickets_vencidos()

    print("Resultado:", resultado)
    assert resultado["revisados"] == 2
    assert resultado["archivados"] == ["dddd0004-0000-0000-0000-000000000000", "dddd0008-0000-0000-0000-000000000000"]
    assert resultado["fallidos"] == []

    get_mock.assert_called_once()
    assert get_mock.call_args.kwargs["params"] == {"garantia_vencida": "true"}
    assert patch_mock.call_count == 2
    assert mock_email.call_count == 2
    print("[OK] Consulta tickets vencidos, archiva cada uno y manda el email\n")


def test_sin_tickets_vencidos_no_archiva_nada():
    mock_get = MagicMock(status_code=200, json=lambda: {"data": []})
    with _mock_auth, \
         patch("archivado_logic.requests.get", return_value=mock_get), \
         patch("archivado_logic.requests.patch") as patch_mock:
        resultado = archivar_tickets_vencidos()

    assert resultado == {"revisados": 0, "archivados": [], "fallidos": []}
    patch_mock.assert_not_called()
    print("[OK] Sin tickets vencidos, no llama a archivar\n")


def test_un_ticket_falla_no_detiene_a_los_demas():
    tickets_vencidos = [
        {"ticket_id": "ticket-malo"},
        {"ticket_id": "ticket-bueno"},
    ]
    mock_get = MagicMock(status_code=200, json=lambda: {"data": tickets_vencidos})

    def patch_side_effect(url, **kwargs):
        if "ticket-malo" in url:
            return MagicMock(status_code=500, text="error interno")
        return MagicMock(status_code=200, json=lambda: {"data": {}})

    with _mock_auth, _mock_email, \
         patch("archivado_logic.requests.get", return_value=mock_get), \
         patch("archivado_logic.requests.patch", side_effect=patch_side_effect):
        resultado = archivar_tickets_vencidos()

    print("Resultado:", resultado)
    assert resultado["archivados"] == ["ticket-bueno"]
    assert resultado["fallidos"] == ["ticket-malo"]
    print("[OK] Un fallo no detiene el resto del lote\n")


def test_backend_get_rechazado_lanza_error():
    mock_get = MagicMock(status_code=500, text="error interno")
    with _mock_auth, patch("archivado_logic.requests.get", return_value=mock_get):
        try:
            archivar_tickets_vencidos()
            print("[FALLO] Deberia haber lanzado RuntimeError")
        except RuntimeError as e:
            print(f"[OK] Lanza RuntimeError cuando el backend rechaza la consulta: {e}\n")


if __name__ == "__main__":
    test_archiva_todos_los_tickets_vencidos()
    test_sin_tickets_vencidos_no_archiva_nada()
    test_un_ticket_falla_no_detiene_a_los_demas()
    test_backend_get_rechazado_lanza_error()
    print("Listo.")
