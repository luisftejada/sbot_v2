"""fix orders table nullable fields

Revision ID: 654d7e976fec
Revises: f8d66dc4cc71
Create Date: 2024-12-08 17:20:40.579759

"""
from typing import Sequence, Union

from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "654d7e976fec"
down_revision: Union[str, None] = "f8d66dc4cc71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("orders", "buy_price", existing_type=mysql.DECIMAL(precision=10, scale=2), nullable=True)
    op.alter_column("orders", "filled", existing_type=mysql.DECIMAL(precision=10, scale=2), nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("orders", "filled", existing_type=mysql.DECIMAL(precision=10, scale=2), nullable=False)
    op.alter_column("orders", "buy_price", existing_type=mysql.DECIMAL(precision=10, scale=2), nullable=False)
    # ### end Alembic commands ###
