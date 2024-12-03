"""Initial migration

Revision ID: 62bdd93a4a70
Revises:
Create Date: 2024-12-01 21:41:12.012388

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62bdd93a4a70"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("order_id", sa.String(length=255), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("executed", sa.DateTime(), nullable=True),
        sa.Column("type", sa.Enum("BUY", "SELL", name="ordertype"), nullable=False),
        sa.Column("buy_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("sell_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("status", sa.Enum("INITIAL", "CREATED", "EXECUTED", name="orderstatus"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("filled", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("benefit", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("orders")
    # ### end Alembic commands ###
