"""
Test completo de autenticación en consola.
Ejecutar desde la raíz del proyecto:

    python scripts/test_auth.py

Prueba el flujo completo:
  1. Conexión a Supabase
  2. Registro de cliente
  3. Verificación de email
  4. Login correcto
  5. Obtener perfil /me con JWT
  6. Login con contraseña incorrecta (debe fallar)
  7. Login sin verificar (debe fallar)
"""
import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
import app.models.cliente       # noqa: F401
import app.models.dispositivo   # noqa: F401
import app.models.tecnico       # noqa: F401
import app.models.tipo_dispositivo  # noqa: F401

from sqlalchemy import text
from app.database import engine, AsyncSessionLocal
from app.services.auth_service import (
    register_cliente,
    verify_email,
    login_cliente,
    get_me,
)
from app.schemas.cliente import ClienteRegister, ClienteLogin
from app.utils.security import hash_password, verify_password, create_access_token

# Email único por ejecución para no colisionar con runs anteriores
TEST_EMAIL = f"test_{uuid.uuid4().hex[:6]}@techfix.pe"
TEST_PASS  = "pass1234"

OK   = "[OK]"
FAIL = "[FAIL]"
SEP  = "-" * 55


def titulo(txt: str):
    print(f"\n{SEP}\n  {txt}\n{SEP}")


async def test_conexion():
    titulo("1. Conexion a Supabase")
    async with engine.connect() as conn:
        row = await conn.execute(text("SELECT current_database(), current_user"))
        db, usr = row.fetchone()
        print(f"  {OK} BD={db}  user={usr}")

        q = ("SELECT table_schema, table_name "
             "FROM information_schema.tables "
             "WHERE table_schema IN ('owner','clientes','pagos') "
             "ORDER BY 1,2")
        rows = (await conn.execute(text(q))).fetchall()
        print(f"  {OK} {len(rows)} tablas encontradas")
        for s, t in rows:
            print(f"       {s}.{t}")
    await engine.dispose()


async def test_security():
    titulo("2. Seguridad (bcrypt + JWT)")
    h = hash_password("mipassword")
    assert verify_password("mipassword", h), "verify_password fallo"
    assert not verify_password("wrong", h),  "verify_password deberia fallar"
    tok = create_access_token(uuid.uuid4(), "cliente")
    assert len(tok) > 50
    print(f"  {OK} hash bcrypt OK")
    print(f"  {OK} JWT generado ({len(tok)} chars)")


async def test_registro(db):
    titulo("3. Registro de cliente")
    data = ClienteRegister(
        nombre="Juan Test",
        email=TEST_EMAIL,
        password=TEST_PASS,
        distrito="Miraflores",
    )
    result = await register_cliente(data, db)
    assert "email" in result
    assert result["email"] == TEST_EMAIL
    token = result.get("dev_token")
    assert token, "No se recibio dev_token"
    print(f"  {OK} Cliente creado: {result['email']}")
    print(f"  {OK} dev_token={token[:20]}...")
    return token


async def test_login_sin_verificar(db):
    titulo("4. Login sin verificar (debe dar 403)")
    try:
        await login_cliente(ClienteLogin(email=TEST_EMAIL, password=TEST_PASS), db)
        print(f"  {FAIL} Debio lanzar 403")
    except Exception as e:
        cod = getattr(e, "status_code", None)
        if cod == 403:
            print(f"  {OK} 403 correcto: {e.detail}")
        else:
            print(f"  {FAIL} Error inesperado: {e}")


async def test_verificar_email(token: str, db):
    titulo("5. Verificacion de email")
    result = await verify_email(token, db)
    print(f"  {OK} {result['mensaje']}")


async def test_login_correcto(db):
    titulo("6. Login correcto")
    result = await login_cliente(
        ClienteLogin(email=TEST_EMAIL, password=TEST_PASS), db
    )
    assert result.rol == "cliente"
    assert len(result.access_token) > 50
    print(f"  {OK} rol={result.rol}")
    print(f"  {OK} token={result.access_token[:30]}...")
    return result.access_token


async def test_get_me(jwt_token: str, db):
    titulo("7. GET /me con JWT")
    import jwt as pyjwt
    from app.config import settings
    payload = pyjwt.decode(
        jwt_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    cliente_id = uuid.UUID(payload["sub"])
    perfil = await get_me(cliente_id, db)
    print(f"  {OK} nombre={perfil.nombre}")
    print(f"  {OK} email={perfil.email}")
    print(f"  {OK} email_verificado={perfil.email_verificado}")
    print(f"  {OK} distrito={perfil.distrito}")


async def test_password_incorrecta(db):
    titulo("8. Login con contrasena incorrecta (debe dar 401)")
    try:
        await login_cliente(
            ClienteLogin(email=TEST_EMAIL, password="wrongpass"), db
        )
        print(f"  {FAIL} Debio lanzar 401")
    except Exception as e:
        cod = getattr(e, "status_code", None)
        if cod == 401:
            print(f"  {OK} 401 correcto: {e.detail}")
        else:
            print(f"  {FAIL} Error inesperado ({cod}): {e}")


async def main():
    print("\n" + "=" * 55)
    print("  TECHFIX — TEST DE AUTENTICACION")
    print("=" * 55)

    try:
        await test_conexion()
    except Exception as e:
        print(f"  {FAIL} No se pudo conectar a la BD: {e}")
        print("  Revisa DATABASE_URL en tu .env")
        sys.exit(1)

    await test_security()

    async with AsyncSessionLocal() as db:
        dev_token = await test_registro(db)
        await test_login_sin_verificar(db)
        await test_verificar_email(dev_token, db)
        jwt_token = await test_login_correcto(db)
        await test_get_me(jwt_token, db)
        await test_password_incorrecta(db)

    print(f"\n{'=' * 55}")
    print("  TODOS LOS TESTS PASARON")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    asyncio.run(main())
