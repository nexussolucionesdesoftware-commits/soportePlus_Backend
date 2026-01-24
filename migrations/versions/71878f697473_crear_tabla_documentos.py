"""Crear tabla Documentos

Revision ID: 71878f697473
Revises: 800ca0dc7a0c
Create Date: 2026-01-24 11:59:34.990826

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "71878f697473"
down_revision = "800ca0dc7a0c"
branch_labels = None
depends_on = None


def upgrade():
    # SOLO CREAMOS LA TABLA DOCUMENTOS
    op.create_table(
        "Documentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre_original", sa.String(length=255), nullable=False),
        sa.Column("nombre_almacenado", sa.String(length=255), nullable=False),
        sa.Column("ruta_relativa", sa.String(length=500), nullable=False),
        sa.Column("mimetype", sa.String(length=100), nullable=True),
        sa.Column("tamano", sa.Integer(), nullable=True),
        sa.Column("Id_Tiquet", sa.Integer(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["Id_Tiquet"],
            ["Tiquet.Id_Tiquet"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre_almacenado"),
    )


def downgrade():
    # SOLO BORRAMOS LA TABLA DOCUMENTOS SI HACEMOS ROLLBACK
    op.drop_table("Documentos")
