"""添加佣金系统相关表

Revision ID: add_commission_system_tables
Revises: 474dcc751804
Create Date: 2025-05-27 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_commission_system_tables'
down_revision = '474dcc751804'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 commission_config 表
    op.create_table('commission_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    
    # 创建 user_commission_balance 表
    op.create_table('user_commission_balance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_address', sa.String(length=64), nullable=False),
        sa.Column('total_earned', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('available_balance', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('withdrawn_amount', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('frozen_amount', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_address')
    )
    
    # 检查 commission_withdrawal 表是否存在，如果不存在则创建
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'commission_withdrawal' not in inspector.get_table_names():
        op.create_table('commission_withdrawal',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_address', sa.String(length=64), nullable=False),
            sa.Column('amount', sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column('currency', sa.String(length=10), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('transaction_hash', sa.String(length=128), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('processed_at', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    # 删除表（按相反顺序）
    op.drop_table('commission_withdrawal')
    op.drop_table('user_commission_balance')
    op.drop_table('commission_config') 