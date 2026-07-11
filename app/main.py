import logging

from fastapi import FastAPI
from app.core.config import settings
from app.auth import router as auth_router
from app.routers import clientes, dispositivos, catalogo, pagos, tickets, tecnicos, adjuntos

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TechFix API", version="1.0.0", debug=settings.DEBUG_MODE)

app.include_router(auth_router.router,      prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(clientes.router,         prefix="/api/v1/clientes",     tags=["Clientes"])
app.include_router(tickets.router,          prefix="/api/v1/tickets",      tags=["Tickets"])
app.include_router(dispositivos.router,     prefix="/api/v1/dispositivos", tags=["Dispositivos"])
app.include_router(adjuntos.router,         prefix="/api/v1/adjuntos",     tags=["Adjuntos"])
app.include_router(catalogo.router,         prefix="/api/v1/catalogo",     tags=["Catálogo"])
app.include_router(pagos.router,            prefix="/api/v1/pagos",        tags=["Pagos"])
app.include_router(tecnicos.router,         prefix="/api/v1/tecnicos",     tags=["Tecnicos"])

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
