"""add_error_message_field

Revision ID: 98fa7c6d1e33
Revises: 98fa7c6d1e32
Create Date: 2025-05-16 20:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98fa7c6d1e33'
down_revision = '98fa7c6d1e32'
branch_labels = None
depends_on = None


def upgrade():
    # 添加error_message字段到assets表
    op.add_column('assets', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade():
    # 删除字段
    op.drop_column('assets', 'error_message') 