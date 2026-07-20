"""Reemplazar uq_dispositivo_cliente_serie por índice único filtrado

En SQL Server, un UNIQUE constraint normal trata NULL como un valor más:
solo permite una fila con (cliente_id=X, numero_serie=NULL). Como
numero_serie es opcional, esto impedía registrar un segundo dispositivo sin
número de serie para el mismo cliente (IntegrityError 23000). Se reemplaza
por un índice único filtrado que solo aplica cuando numero_serie no es NULL.

Revision ID: 004
Revises: 003
Create Date: 2026-07-20
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_dispositivo_cliente_serie", "dispositivo", schema="clientes", type_="unique"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_dispositivo_cliente_serie "
        "ON clientes.dispositivo (cliente_id, numero_serie) "
        "WHERE numero_serie IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_dispositivo_cliente_serie ON clientes.dispositivo")
    op.create_unique_constraint(
        "uq_dispositivo_cliente_serie", "dispositivo", ["cliente_id", "numero_serie"], schema="clientes"
    )
