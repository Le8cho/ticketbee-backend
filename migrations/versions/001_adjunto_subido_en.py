"""Rename adjunto.creado_en → subido_en and add ticket_id index

Revision ID: 001
Revises:
Create Date: 2026-07-10
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # La columna en Azure SQL se llama creado_en; nuestro modelo espera subido_en
    op.execute("EXEC sp_rename 'clientes.adjunto.creado_en', 'subido_en', 'COLUMN'")

    # Índice en ticket_id para acelerar las consultas de listar adjuntos
    op.create_index(
        "ix_clientes_adjunto_ticket_id",
        "adjunto",
        ["ticket_id"],
        schema="clientes",
    )


def downgrade() -> None:
    op.drop_index("ix_clientes_adjunto_ticket_id", table_name="adjunto", schema="clientes")
    op.execute("EXEC sp_rename 'clientes.adjunto.subido_en', 'creado_en', 'COLUMN'")
