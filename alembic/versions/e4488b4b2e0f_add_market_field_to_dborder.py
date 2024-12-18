"""add market field to DbOrder

Revision ID: e4488b4b2e0f
Revises: 654d7e976fec
Create Date: 2024-12-18 15:13:10.433358

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4488b4b2e0f"
down_revision: Union[str, None] = "654d7e976fec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("orders", sa.Column("market", sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("orders", "market")
    # ### end Alembic commands ###
