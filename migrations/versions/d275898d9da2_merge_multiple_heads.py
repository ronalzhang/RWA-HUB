"""merge multiple heads

Revision ID: d275898d9da2
Revises: 98fa7c6d1e33, add_onchain_history, 91f4a8c7e9d3
Create Date: 2025-05-26 16:15:41.796647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd275898d9da2'
down_revision = ('98fa7c6d1e33', 'add_onchain_history', '91f4a8c7e9d3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
