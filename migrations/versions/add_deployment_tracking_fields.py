"""add_deployment_tracking_fields

Revision ID: 98fa7c6d1e32
Revises: 6347f6f6f92f
Create Date: 2025-05-16 19:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98fa7c6d1e32'
down_revision = '6347f6f6f92f'
branch_labels = None
depends_on = None


def upgrade():
    # 添加deployment_in_progress和deployment_started_at字段到assets表
    op.add_column('assets', sa.Column('deployment_in_progress', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('assets', sa.Column('deployment_started_at', sa.DateTime(), nullable=True))


def downgrade():
    # 删除字段
    op.drop_column('assets', 'deployment_started_at')
    op.drop_column('assets', 'deployment_in_progress') 