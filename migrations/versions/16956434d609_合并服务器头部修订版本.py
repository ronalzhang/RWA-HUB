"""合并服务器头部修订版本

Revision ID: 16956434d609
Revises: a6a37b18172a, ce5a4d540c25
Create Date: 2025-05-27 01:33:17.770972

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '16956434d609'
down_revision = ('a6a37b18172a', 'ce5a4d540c25')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
