from fastapi import FastAPI
from app.config import settings
from app.routers import auth, dispositivos, catalogo, pagos, tickets_router, clientes, adjuntos


app = FastAPI(title="TechFix API", version="1.0.0", debug=settings.DEBUG)

app.include_router(auth.router,               prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(clientes.router,           prefix="/api/v1/clientes",     tags=["Clientes"])
app.include_router(tickets_router.router,     prefix="/api/v1/tickets",      tags=["Tickets"])
app.include_router(dispositivos.router,       prefix="/api/v1/dispositivos", tags=["Dispositivos"])
app.include_router(adjuntos.router,           prefix="/api/v1/adjuntos",     tags=["Adjuntos"])
app.include_router(catalogo.router,           prefix="/api/v1/catalogo",     tags=["Catálogo"])
app.include_router(pagos.router,              prefix="/api/v1/pagos",        tags=["Pagos"])

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}