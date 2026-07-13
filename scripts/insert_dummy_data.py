import sys
import os
import uuid
import datetime

# Asegurar que importemos desde la raiz del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock create_async_engine so app.core.database doesn't crash from missing ODBC
import sqlalchemy.ext.asyncio
sqlalchemy.ext.asyncio.create_async_engine = lambda *args, **kwargs: None

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.cliente import Cliente
from app.models.tecnico import Tecnico
from app.models.tipo_dispositivo import TipoDispositivo
from app.models.dispositivo import Dispositivo
from app.models.servicio import Servicio
from app.models.ticket import Ticket, TicketEstado, TicketDispositivo
from app.core.config import settings

def main():
    # Convertimos la URL de ODBC a pymssql para poder correrlo local sin drivers de Microsoft
    db_url = settings.DATABASE_URL.replace("mssql+aioodbc", "mssql+pymssql")
    db_url = db_url.split("?")[0] # quitar parametros odbc
    
    # Manejar caso usuario@servidor para pymssql si es necesario, 
    # pero primero intentamos la normal
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        # Verificar conexion
        db.execute(text("SELECT 1"))
    except Exception as e:
        # Si falla probamos con usadmin@server-ticketfix
        print("Fallo conexion, intentando fix de username de Azure SQL para pymssql...")
        db_url = db_url.replace("usadmin:", "usadmin@server-ticketfix:")
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
    try:
        print("Conectado! Creando datos dummy...")
        
        # 1. Crear Cliente
        cliente = Cliente(
            nombre="cliente_prueba",
            email="nccamiloxd@gmail.com",
            distrito="Lima"
        )
        db.add(cliente)
        
        # 2. Crear Tecnico
        tecnico = Tecnico(
            nombre="tecnico_test",
            email="cludiogonsales@gmail.com"
        )
        db.add(tecnico)
        
        # 3. Crear Tipo Dispositivo (solo si no existe uno)
        # Usamos try except o consultamos primero
        tipo_disp = db.query(TipoDispositivo).filter_by(nombre="Laptop Prueba").first()
        if not tipo_disp:
            tipo_disp = TipoDispositivo(nombre="Laptop Prueba")
            db.add(tipo_disp)
        
        # 4. Crear Servicio (solo si no existe)
        servicio = db.query(Servicio).filter_by(nombre="Reparación Dummy").first()
        if not servicio:
            servicio = Servicio(
                nombre="Reparación Dummy",
                tipo_servicio="CORRECTIVO",
                precio_base=45.00
            )
            db.add(servicio)
            
        db.commit()
        
        # 5. Crear Dispositivo para el cliente
        disp = Dispositivo(
            cliente_id=cliente.cliente_id,
            tipo_dispositivo_id=tipo_disp.tipo_dispositivo_id,
            marca="Dell",
            modelo="XPS 15",
            numero_serie=f"SN-{uuid.uuid4().hex[:8]}"
        )
        db.add(disp)
        db.commit()
        
        # 6. Crear 3 Tickets en espera de pago (monto <= 50)
        for i in range(1, 4):
            ticket = Ticket(
                cliente_id=cliente.cliente_id,
                servicio_id=servicio.servicio_id,
                tecnico_id=tecnico.tecnico_id,
                estado=TicketEstado.EN_ESPERA_PAGO,
                precio_base=45.00,
                precio_final=45.00,
                descripcion=f"Incidente de prueba #{i}"
            )
            db.add(ticket)
            db.flush() # Para obtener el ticket_id
            
            # Asociar el ticket con el dispositivo
            ticket_disp = TicketDispositivo(
                ticket_id=ticket.ticket_id,
                dispositivo_id=disp.dispositivo_id
            )
            db.add(ticket_disp)
            print(f"Creado Ticket ID: {ticket.ticket_id} | Precio: S/. {ticket.precio_final}")
            
        db.commit()
        print("\n✅ Todos los datos dummy (Cliente, Tecnico, y 3 Tickets) creados exitosamente.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear los datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
