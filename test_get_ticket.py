import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(text("SELECT ticket_id, precio_final FROM clientes.ticket WHERE estado = 'EN_ESPERA_PAGO'"))
        tickets = result.fetchall()
        for t in tickets:
            print(f"Ticket ID: {t.ticket_id} - Precio: {t.precio_final}")

asyncio.run(main())
