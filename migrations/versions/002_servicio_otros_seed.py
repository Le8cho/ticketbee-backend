"""Seed catalog service 'Otros' (tipo_servicio=OTROS)

Revision ID: 002
Revises: 001
Create Date: 2026-07-18
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

NOMBRE_OTROS = "Otro / Diagnóstico personalizado"


def upgrade() -> None:
    conn = op.get_bind()
    existe = conn.execute(
        sa.text("SELECT 1 FROM owner.SERVICIO WHERE tipo_servicio = 'OTROS'")
    ).fetchone()
    if existe:
        return

    conn.execute(
        sa.text(
            "INSERT INTO owner.SERVICIO (servicio_id, nombre, tipo_servicio, precio_base, activo) "
            "VALUES (:id, :nombre, 'OTROS', :precio_base, 1)"
        ),
        {"id": str(uuid.uuid4()), "nombre": NOMBRE_OTROS, "precio_base": 0.01},
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM owner.SERVICIO WHERE tipo_servicio = 'OTROS'")
    )
