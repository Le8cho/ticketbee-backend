import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.auth import router as auth_router
from app.routers import clientes, dispositivos, catalogo, pagos, tickets, tecnicos, adjuntos, payments

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="TechFix API", version="1.0.0", debug=settings.DEBUG_MODE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Los tags de agrupación en Swagger se definen por endpoint (no aquí) con el
# esquema "<Módulo>-<Rol>": Cliente, Tecnico, Compartido o Publico. Así se ve
# de un vistazo en /docs qué rol necesita cada operación para probarla.
app.include_router(auth_router.router,      prefix="/api/v1/auth")
app.include_router(clientes.router,         prefix="/api/v1/clientes")
app.include_router(tickets.router,          prefix="/api/v1/tickets")
app.include_router(dispositivos.router,     prefix="/api/v1/dispositivos")
app.include_router(adjuntos.router,         prefix="/api/v1/adjuntos")
app.include_router(catalogo.router,         prefix="/api/v1/catalogo")
app.include_router(pagos.router,            prefix="/api/v1/pagos",        tags=["Pagos"])
app.include_router(tecnicos.router,         prefix="/api/v1/tecnicos")
app.include_router(payments.router)
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
