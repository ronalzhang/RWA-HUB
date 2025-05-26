"""合并多个头部修订版本

Revision ID: 7614b3f415af
Revises: add_commission_system_tables, 98fa7c6d1e33, add_onchain_history, 91f4a8c7e9d3
Create Date: 2025-05-27 01:31:25.597573

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7614b3f415af'
down_revision = ('add_commission_system_tables', '98fa7c6d1e33', 'add_onchain_history', '91f4a8c7e9d3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
