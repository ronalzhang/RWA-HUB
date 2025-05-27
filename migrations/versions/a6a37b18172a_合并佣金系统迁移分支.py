"""合并佣金系统迁移分支

Revision ID: a6a37b18172a
Revises: 72c1661ccc2b, add_commission_system_tables, d275898d9da2
Create Date: 2025-05-27 00:43:03.776443

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6a37b18172a'
down_revision = ('72c1661ccc2b', 'add_commission_system_tables', 'd275898d9da2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
