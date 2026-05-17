from fastapi import FastAPI
from app.config import settings
from app.routers import auth, tickets, dispositivos, catalogo, pagos

app = FastAPI(title="TechFix API", version="1.0.0", debug=settings.DEBUG)

app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(tickets.router,      prefix="/api/v1/tickets",      tags=["Tickets"])
app.include_router(dispositivos.router, prefix="/api/v1/dispositivos", tags=["Dispositivos"])
app.include_router(catalogo.router,     prefix="/api/v1/catalogo",     tags=["Catálogo"])
app.include_router(pagos.router,        prefix="/api/v1/pagos",        tags=["Pagos"])

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}