import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cliente_repository import ClienteRepository
from app.schemas.cliente import ClienteListItem, ClienteProfile, DispositivoConTickets, TicketResumen


class ClienteService:

    def __init__(self, db: AsyncSession):
        self.repo = ClienteRepository(db)

    async def list_clientes(
        self,
        estado_ticket: str | None = None,
        distrito: str | None = None,
        fecha_desde: datetime | None = None,
        tipo_ultimo_ticket: str | None = None,
    ) -> list[ClienteListItem]:
        """Devuelve el listado de clientes para el panel del técnico (SD-17)."""
        rows = await self.repo.list_clientes(
            estado_ticket=estado_ticket,
            distrito=distrito,
            fecha_desde=fecha_desde,
            tipo_ultimo_ticket=tipo_ultimo_ticket,
        )
        return [
            ClienteListItem(
                cliente_id=row.Cliente.cliente_id,
                nombre=row.Cliente.nombre,
                email=row.Cliente.email,
                distrito=row.Cliente.distrito,
                creado_en=row.Cliente.creado_en,
                tickets_activos=row.tickets_activos,
                ultimo_ticket_estado=row.ultimo_ticket_estado,
            )
            for row in rows
        ]

    async def get_cliente_profile(self, cliente_id: uuid.UUID) -> ClienteProfile | None:
        """Devuelve el perfil completo del cliente con dispositivos y tickets (SD-17)."""
        cliente = await self.repo.get_cliente_profile(cliente_id)
        if not cliente:
            return None

        dispositivo_ids = [d.dispositivo_id for d in cliente.dispositivos]
        ticket_rows = await self.repo.get_tickets_por_dispositivos(dispositivo_ids)

        # Agrupa tickets por dispositivo_id en memoria
        tickets_por_disp: dict[uuid.UUID, list[TicketResumen]] = {
            d.dispositivo_id: [] for d in cliente.dispositivos
        }
        for row in ticket_rows:
            tickets_por_disp[row.dispositivo_id].append(
                TicketResumen(
                    ticket_id=row.Ticket.ticket_id,
                    estado=row.Ticket.estado,
                    servicio_nombre=row.servicio_nombre,
                    precio_base=float(row.Ticket.precio_base) if row.Ticket.precio_base else None,
                    precio_final=float(row.Ticket.precio_final) if row.Ticket.precio_final else None,
                    creado_en=row.Ticket.creado_en,
                )
            )

        dispositivos = [
            DispositivoConTickets(
                dispositivo_id=d.dispositivo_id,
                tipo_nombre=d.tipo_dispositivo.nombre if d.tipo_dispositivo else None,
                marca=d.marca,
                modelo=d.modelo,
                numero_serie=d.numero_serie,
                activo=d.activo,
                tickets=tickets_por_disp[d.dispositivo_id],
            )
            for d in cliente.dispositivos
        ]

        return ClienteProfile(
            cliente_id=cliente.cliente_id,
            nombre=cliente.nombre,
            email=cliente.email,
            distrito=cliente.distrito,
            # email_verificado=cliente.email_verificado,
            activo=cliente.activo,
            creado_en=cliente.creado_en,
            dispositivos=dispositivos,
        )
