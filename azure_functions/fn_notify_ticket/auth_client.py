import os
import time

import requests

_cached_token: str | None = None
_cached_expiry: float = 0


def obtener_token() -> str:
    """Login como tecnico de servicio en Supabase Auth. Cachea el JWT hasta que vence."""
    global _cached_token, _cached_expiry

    if _cached_token and time.time() < _cached_expiry - 60:
        return _cached_token

    url = f"{os.environ['SUPABASE_URL']}/auth/v1/token?grant_type=password"
    headers = {"apikey": os.environ["SUPABASE_ANON_KEY"], "Content-Type": "application/json"}
    payload = {
        "email": os.environ["TECNICO_SERVICE_EMAIL"],
        "password": os.environ["TECNICO_SERVICE_PASSWORD"],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"No se pudo autenticar la cuenta de servicio: {resp.status_code} {resp.text}")

    data = resp.json()
    _cached_token = data["access_token"]
    _cached_expiry = time.time() + data["expires_in"]
    return _cached_token


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {obtener_token()}"}
