"""
CLI interactivo de autenticación TechFix.
Ejecutar: python scripts/auth_cli.py
"""
import asyncio, sys, os, getpass
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.models.cliente
import app.models.dispositivo
import app.models.tecnico
import app.models.tipo_dispositivo

from app.database import AsyncSessionLocal
from app.services.auth_service import (
    register_cliente, verify_email, resend_verification,
    login_cliente, get_me,
)
from app.schemas.cliente import ClienteRegister, ClienteLogin

SEP = "─" * 45

def menu():
    print(f"\n{SEP}")
    print("  TechFix — Auth CLI")
    print(SEP)
    print("  1. Registrar cliente")
    print("  2. Verificar email (con token)")
    print("  3. Iniciar sesion")
    print("  4. Ver mi perfil (necesitas token JWT)")
    print("  5. Reenviar verificacion")
    print("  0. Salir")
    print(SEP)
    return input("  Elige una opcion: ").strip()


async def registrar():
    print(f"\n--- REGISTRO ---")
    nombre   = input("  Nombre completo : ").strip()
    email    = input("  Email           : ").strip()
    password = getpass.getpass("  Contrasena      : ")
    distrito = input("  Distrito        : ").strip()

    async with AsyncSessionLocal() as db:
        try:
            data = ClienteRegister(nombre=nombre, email=email,
                                   password=password, distrito=distrito)
            res = await register_cliente(data, db)
            print(f"\n  OK: {res['mensaje']}")
            print(f"\n  >>> Copia este token para verificar tu email:")
            print(f"      {res['dev_token']}")
        except Exception as e:
            detail = getattr(e, 'detail', str(e))
            print(f"\n  ERROR: {detail}")


async def verificar():
    print(f"\n--- VERIFICAR EMAIL ---")
    token = input("  Pega el token de verificacion: ").strip()

    async with AsyncSessionLocal() as db:
        try:
            res = await verify_email(token, db)
            print(f"\n  OK: {res['mensaje']}")
        except Exception as e:
            print(f"\n  ERROR: {getattr(e, 'detail', str(e))}")


async def iniciar_sesion():
    print(f"\n--- LOGIN ---")
    email    = input("  Email     : ").strip()
    password = getpass.getpass("  Contrasena: ")

    async with AsyncSessionLocal() as db:
        try:
            res = await login_cliente(ClienteLogin(email=email, password=password), db)
            print(f"\n  OK - rol: {res.rol}")
            print(f"\n  Tu JWT (guardalo para usar /me):")
            print(f"  {res.access_token}")
        except Exception as e:
            print(f"\n  ERROR: {getattr(e, 'detail', str(e))}")


async def ver_perfil():
    print(f"\n--- MI PERFIL ---")
    import jwt as pyjwt, uuid
    from app.config import settings
    token = input("  Pega tu JWT: ").strip()

    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY,
                               algorithms=[settings.ALGORITHM])
        cliente_id = uuid.UUID(payload["sub"])
    except Exception:
        print("  ERROR: Token invalido o expirado")
        return

    async with AsyncSessionLocal() as db:
        try:
            perfil = await get_me(cliente_id, db)
            print(f"\n  Nombre   : {perfil.nombre}")
            print(f"  Email    : {perfil.email}")
            print(f"  Distrito : {perfil.distrito}")
            print(f"  Verificado: {perfil.email_verificado}")
            print(f"  Activo   : {perfil.activo}")
            print(f"  Registro : {str(perfil.creado_en)[:19]}")
        except Exception as e:
            print(f"\n  ERROR: {getattr(e, 'detail', str(e))}")


async def reenviar():
    print(f"\n--- REENVIAR VERIFICACION ---")
    email = input("  Email: ").strip()

    async with AsyncSessionLocal() as db:
        res = await resend_verification(email, db)
        print(f"\n  {res['mensaje']}")
        if "dev_token" in res:
            print(f"  Token: {res['dev_token']}")


async def main():
    print("\n  Conectando a Supabase...")
    from sqlalchemy import text
    from app.database import engine
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await engine.dispose()
    print("  Conexion OK")

    while True:
        opcion = menu()
        if   opcion == "1": await registrar()
        elif opcion == "2": await verificar()
        elif opcion == "3": await iniciar_sesion()
        elif opcion == "4": await ver_perfil()
        elif opcion == "5": await reenviar()
        elif opcion == "0": print("\n  Hasta luego!\n"); break
        else: print("  Opcion invalida")


if __name__ == "__main__":
    asyncio.run(main())
