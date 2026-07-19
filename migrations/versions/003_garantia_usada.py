"""Add garantia.usada (garantía de un solo uso)

Revision ID: 003
Revises: 002
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "garantia",
        sa.Column(
            "usada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="clientes",
    )


def downgrade() -> None:
    op.drop_column("garantia", "usada", schema="clientes")
