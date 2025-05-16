"""add_asset_status_history

Revision ID: add_asset_status_history
Revises: add_deployment_tracking_fields
Create Date: 2025-05-17 00:05:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_asset_status_history'
down_revision = 'add_deployment_tracking_fields'
branch_labels = None
depends_on = None


def upgrade():
    # 创建资产状态历史表
    op.create_table('asset_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.Integer(), nullable=False),
        sa.Column('new_status', sa.Integer(), nullable=False),
        sa.Column('change_time', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('change_reason', sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 添加索引
    op.create_index(op.f('ix_asset_status_history_asset_id'), 'asset_status_history', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_status_history_change_time'), 'asset_status_history', ['change_time'], unique=False)


def downgrade():
    # 删除索引
    op.drop_index(op.f('ix_asset_status_history_change_time'), table_name='asset_status_history')
    op.drop_index(op.f('ix_asset_status_history_asset_id'), table_name='asset_status_history')
    
    # 删除表
    op.drop_table('asset_status_history') 